import sqlite3
import re
import time

from bs4 import BeautifulSoup
# from geopy.geocoders import Nominatim as Geo

from scraper import BaseScraper


def recognize_price_text(price_text):
    pattern = re.compile(r"\$\s?[\d,]+")
    match = pattern.search(price_text)
    # cat 0: no digit at all
    if not match:
        print "cat 0:", price_text
    # cat 1: single number
    elif len(match) == 1:
        print "cat 1:", price_text
    # cat 2: two numbers
    elif len(match) == 2:
        print "cat 2:", price_text
    else:
        print "mismatch:", price_text

    pass


class Parser(object):
    scr_db = BaseScraper.db
    tgt_db = "./data/database.db"

    def __init__(self):
        self.html = ""
        self.address = ""
        self.hash_id = 0
        self.property_type = ""
        self.postcode = ""
        self.state = ""
        self.price_text = ""
        self.open_date = ""
        self.rooms = "-,-,-"  # bed,bath,park
        self._tgt_db_conn = sqlite3.connect(self.tgt_db)
        self.cur = self._tgt_db_conn.cursor()
        self.write_queue_len = 0
        pass

    def _fetchonedict(self, cur):
        assert isinstance(cur, sqlite3.Cursor)
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

        with sqlite3.connect(self.tgt_db) as conn:
            # get the parsed list of hash id
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

        with sqlite3.connect(self.scr_db) as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM tbl_html_text LIMIT ?", (line_num,))
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
                        self.html = rs["html_text"]
                        self.hash_id = rs['hash_id']

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
        price_text = article.find("p", class_="priceText")
        if not price_text:
            price_text = article.find("p", class_="contactAgent")
        if not price_text:
            price_text = article.find("span", class_="price rui-truncate")

        if price_text:
            self.price_text = price_text.get_text()
            # print self.price_text

        # todo li, class='badge openTime'
        # s = article.find("li", class_="badge openTime")
        # if s:
        #     print s.get_text(), len(article.find_all("li", class_="badge openTime"))

        # get rooms
        self.rooms = "-,-,-"
        rooms = article.find("dl", class_="rui-property-features rui-clearfix")
        if rooms:
            room_text = rooms.get_text()
            # print room_text, "===>", self._parse_rooms(room_text)
            self.rooms = self._parse_rooms(room_text)

    def _parse_rooms(self, room_text):
        """
        :return: [1,2,3] for [bed,bath,car]
        """
        assert isinstance(room_text, basestring)
        rooms = ["-", "-", "-"]
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
        return ",".join(rooms)

    def test_db(self):
        with sqlite3.connect(self.tgt_db) as conn:
            cur = conn.cursor()
            cur.execute(
                """CREATE TABLE IF NOT EXISTS `tbl_property_ad` (
                        `hash_id`	INTEGER NOT NULL UNIQUE,
                        `id`	INTEGER PRIMARY KEY AUTOINCREMENT,
                        `address`	TEXT NOT NULL,
                        `price`	INTEGER,
                        `price_text`	TEXT,
                        `agent_name`	TEXT,
                        `agent_company`	TEXT,
                        `raw_list_text`	TEXT,
                        `rooms`	TEXT,
                        `type`	TEXT,
                        `subtype`	TEXT,
                        `lat`	NUMERIC,
                        `long`	NUMERIC,
                        `address_nomalized`	TEXT,
                        `state`	TEXT,
                        `postcode`	TEXT
                    );
                    """)
            conn.commit()

    def insert_data(self):
        cur = self.cur

        try:
            cur.execute("INSERT INTO tbl_property_ad (hash_id, address, type, state, postcode, price_text, rooms) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (self.hash_id, self.address, self.property_type, self.state, self.postcode, self.price_text,
                         self.rooms))
        except sqlite3.IntegrityError:
            cur.execute("UPDATE tbl_property_ad SET address = ?, "
                        "type = ?, "
                        "state = ?, "
                        "postcode =?, "
                        "hash_id = ?, "
                        "price_text = ?, "
                        "rooms = ? "
                        "WHERE hash_id = ?",
                        (self.address, self.property_type, self.state, self.postcode, self.hash_id, self.price_text,
                         self.rooms, self.hash_id))
        self.write_queue_len += 1

        if self.write_queue_len > 5000:
            print "save 5000 lines..."
            self._tgt_db_conn.commit()
            self._tgt_db_conn.close()
            self._tgt_db_conn = sqlite3.connect(self.tgt_db)
            self.cur = self._tgt_db_conn.cursor()
            self.write_queue_len = 0


if __name__ == "__main__":
    parser = Parser()
    # parser.scr_db = "./test/scraper_dumps.db"
    # parser.tgt_db = "./test/database.db"
    parser.test_db()
    parser.extract_html_text(10000)




