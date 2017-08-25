import time
import zlib

from bs4 import BeautifulSoup
# from geopy.geocoders import Nominatim as Geo

from scraper import BaseScraper
from price_parser import parse_price_text

from MySQL_connector import db_connector

db = 'realestate_db'


class Parser(object):
    scr_db = 'scraper_dumps'
    tgt_db = 'realestate_db'

    def __init__(self):
        self.html = ""

        self.address = ""
        self.hash_id = 0
        self.property_type = ""
        self.sub_type = ""
        self.ad_id = ""
        self.ad_url = ""
        self.postcode = ""
        self.state = ""
        self.price_text = ""
        self.open_date = ""
        self.room_bed = None
        self.room_bath = None
        self.room_car = None
        self.create_date = ""
        self.last_seen_date = ""
        self.raw_ad_text = ""
        self.price = None
        self.agent_name = ""
        self.agent_company = ""

        self._tgt_db_conn = db_connector(self.tgt_db)
        self.cur = self._tgt_db_conn.cursor()
        self.write_queue_len = 0
        pass

    @staticmethod
    def _fetchonedict(cur):
        data = cur.fetchone()
        if data:
            rs = {}
            for i in range(len(data)):
                col = cur.description[i][0]
                d = data[i]
                rs[col] = d
            return rs
        else:
            return None

    def extract_html_text(self, line_num=1000):
        """
        query html from source database
        call parse function to parse html to structured data
        call insert function to insert to target database
        :return: 
        """

        tic = time.time()
        # get the parsed list of hash id
        conn = db_connector(self.tgt_db)
        cur = conn.cursor()
        cur.execute("SELECT hash_id FROM tbl_property_ad")
        parsed_hash_id = set()
        while True:
            res = cur.fetchone()
            if res:
                parsed_hash_id.add(res[0])
            else:
                break
        pass

        conn = db_connector(self.scr_db)
        cur = conn.cursor()
        cur.execute("SELECT * FROM tbl_html_text LIMIT %s", (line_num,))
        i = 0
        try:
            while True:
                # each row of data
                i += 1
                if not(i % 1000):
                    print "processing %d lines of data. (%f sec)\r" % (i, time.time()-tic)
                    tic = time.time()
                rs = self._fetchonedict(cur)
                if isinstance(rs, dict):
                    # get address only for the first version
                    # if rs['hash_id'] in parsed_hash_id:
                    #     continue
                    self.html = zlib.decompress(str(rs["html_text"])).decode("utf-8")
                    self.hash_id = rs['hash_id']
                    self.create_date = rs["create_date"]
                    self.last_seen_date = rs["last_seen_date"]
                    self.raw_ad_text = rs["ad_text"]

                else:
                    break

                # call parse

                self.parse_html_text()
                self.insert_data()
        finally:
            self._tgt_db_conn.commit()
            self._tgt_db_conn.close()
            print "Saving and closing connection."

    def parse_html_text(self):
        soup = BeautifulSoup(self.html, "html.parser")

        # get type
        article = soup.article
        try:
            self.property_type = article["data-content-type"]
        except (AttributeError, KeyError):
            self.property_type = ""

        # get ad id
        self.ad_id = ""
        try:
            self.ad_id = article["id"]
        except (AttributeError, KeyError):
            self.ad_id = ""

        # get url
        self.ad_url = ""
        if self.ad_id:
            url = article.find("a")['href']
            assert isinstance(url, basestring)
            while url:
                if url[0] == "/" and url.find(self.ad_id[1:]):
                    break
                url = article.find("a")['href']
            self.ad_url = "www.realestate.com.au"+url

        # get subtype
        self.sub_type = ""
        if self.ad_url:
            url_component = url.split("-")
            self.sub_type = url_component[1]

        # get address
        photoviewer = soup.find("div", class_="photoviewer")
        if photoviewer:
            img = photoviewer.find("img")
            try:
                self.address = img['title']
            except (KeyError, AttributeError):
                self.address = ""
                print "Could not found address, hash id:", self.hash_id
                pass
                # what if could not find address in the phtoviewer

        # get postcode
        self.postcode = ""
        if self.address:
            postcode = self.address[-4:].strip()
            if postcode.isdigit():
                self.postcode = postcode

        # get state
        self.state = ""
        if self.postcode:
            t = self.address.split(",")
            t = t[-1]
            state = t.strip().split(" ")[0]
            self.state = state.upper()

        # get price text
        self.price_text = ""
        self.price = None
        price_text = article.find("p", class_="priceText")
        if not price_text:
            price_text = article.find("p", class_="contactAgent")
        if not price_text:
            price_text = article.find("span", class_="price rui-truncate")

        if price_text:
            self.price_text = price_text.get_text()
            self.price = parse_price_text(self.price_text)
            if not isinstance(self.price, float):
                self.price = None

        # todo li, class='badge openTime'
        # s = article.find("li", class_="badge openTime")
        # if s:
        #     print s.get_text(), len(article.find_all("li", class_="badge openTime"))

        # get rooms
        self.room_bed = None
        self.room_bath = None
        self.room_car = None
        rooms = article.find("dl", class_="rui-property-features rui-clearfix")
        if rooms:
            room_text = rooms.get_text()
            # print room_text, "===>", self._parse_rooms(room_text)
            self.room_bed, self.room_bath, self.room_car = self._parse_rooms(room_text)

    def _parse_rooms(self, room_text):
        """
        :return: [1,2,3] for [bed,bath,car]
        """
        assert isinstance(room_text, basestring)
        rooms = [None, None, None]
        s = room_text.split(" ")
        while s:
            text = s.pop(0)
            if text == "Bedrooms":
                num = s[0]
                if num.isdigit():
                    s.pop(0)
                    rooms[0] = num
            elif text == "Bathrooms":
                num = s[0]
                if num.isdigit():
                    s.pop(0)
                    rooms[1] = num
            elif text == "Car":
                if s[0] == "Spaces":
                    s.pop(0)
                    num = s[0]
                    if num.isdigit():
                        s.pop(0)
                        rooms[2] = num
        return rooms

    def test_db(self):
        conn = db_connector(db)
        cur = conn.cursor()
        cur.execute(
            """ CREATE TABLE IF NOT EXISTS`tbl_property_ad` (
                      `id` INT NOT NULL,
                      `hash_id` INT NOT NULL,
                      `address` VARCHAR(100) NULL,
                      `price` INT NULL,
                      `price_text` VARCHAR(100) NULL,
                      `agent_name` VARCHAR(45) NULL,
                      `agent_company` VARCHAR(45) NULL,
                      `raw_list_text` VARCHAR(255) NULL,
                      `room.bed` INT NULL,
                      `room.bath` INT NULL,
                      `room.car` INT NULL,
                      `type` VARCHAR(45) NULL,
                      `subtype` VARCHAR(45) NULL,
                      `lat` DECIMAL NULL,
                      `long` DECIMAL NULL,
                      `address_normalized` VARCHAR(100) NULL,
                      `state` VARCHAR(10) NULL,
                      `postcode` VARCHAR(10) NULL,
                      `ad_url` VARCHAR(255) NULL,
                      `create_date` timestamp NULL DEFAULT NULL,
                      `last_seen_date` timestamp NULL DEFAULT NULL,
                      PRIMARY KEY (`id`,`hash_id`),
                      UNIQUE KEY `id_UNIQUE` (`id`),
                      UNIQUE KEY `hash_id_UNIQUE` (`hash_id`))
                """)
        conn.commit()
        conn.close()

    def insert_data(self):
        cur = self.cur
        cur.execute("INSERT INTO tbl_property_ad "
                    "(hash_id, address, type, subtype,"
                    " state, postcode, price_text, price, "
                    "`room.bed`, `room.bath`, `room.car`, "
                    "`raw_list_text`, `ad_url`,"
                    " `create_date`, `last_seen_date`) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE "
                    "address = %s, type = %s, subtype =%s, "
                    "state = %s, postcode =%s, price_text = %s, price=%s, "
                    "`room.bed` = %s, `room.bath` = %s, `room.car` = %s, "
                    "`raw_list_text`=%s, `ad_url`=%s, "
                    "`create_date`=%s, `last_seen_date`=%s ",
                    (self.hash_id, self.address, self.property_type, self.sub_type,
                     self.state, self.postcode, self.price_text, self.price,
                     self.room_bed, self.room_bath, self.room_car,
                     self.raw_ad_text, self.ad_url,
                     self.create_date, self.last_seen_date,

                     self.address, self.property_type, self.sub_type,
                     self.state, self.postcode, self.price_text, self.price,
                     self.room_bed, self.room_bath, self.room_car,
                     self.raw_ad_text, self.ad_url,
                     self.create_date, self.last_seen_date
                     ))
        self.write_queue_len += 1

        if self.write_queue_len > 5000:
            print "save 5000 lines..."
            self._tgt_db_conn.commit()
            self.write_queue_len = 0


if __name__ == "__main__":
    parser = Parser()
    # parser.scr_db = "./test/scraper_dumps.db"
    # parser.tgt_db = "./test/database.db"
    parser.test_db()
    parser.extract_html_text(10000000)




