# coding:utf-8
# MySQL
from __future__ import print_function

import requests
import mysql.connector
import datetime
import time
from bs4 import BeautifulSoup, element


def db_connector():
    cnx = mysql.connector.connect(user='lyso',
                                  password='lyskey',
                                  host="localhost",
                                  database='realestate_scraper')
    return cnx

sql_create_tbl_html_text = "create table if not exists tbl_html_text(" \
                          "hash_id INT NOT NULL, " \
                          "html_text MEDIUMTEXT NOT NULL, " \
                          "create_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, " \
                          "url TEXT NOT NULL, " \
                          "ad_text VARCHAR(255), " \
                          "last_seen_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, " \
                          "PRIMARY KEY(hash_id) )"

sql_create_tbl_scrap_log = "create table if not exists tbl_scrap_log(" \
                           "scrap_id VARCHAR(255)," \
                           "note VARCHAR(255)," \
                           "timestamp TIMESTAMP NOT NULL DEFAULT current_timestamp);"

class BaseScraper(object):
    def __init__(self):
        self.domain = "www.realestate.com.au"
        self.url_template = "http://www.realestate.com.au/buy/in-%s/list-%s?includeSurrounding=false"
        self.page_num = 1
        self.postcode = 2077
        self.soup = None
        self._conn = db_connector()
        self._cur = self._conn.cursor()
        self.write_queue_len = 0
        self.scrap_log = None

    @staticmethod
    def test_db():
        conn = db_connector()
        cur = conn.cursor()
        cur.execute(sql_create_tbl_html_text)
        cur.execute(sql_create_tbl_scrap_log)
        conn.commit()
        conn.close()

    def log_scrap(self, scrap_id, note=None):
        scrap_id = str(scrap_id)
        if self.has_scraped(scrap_id):
            return False
        self._cur.execute("INSERT INTO tbl_scrap_log (scrap_id, note) VALUES (%s, %s)", (scrap_id, note))
        self._conn.commit()
        self.scrap_log.add(scrap_id)
        return True

    def has_scraped(self, scrap_id):
        if self.scrap_log is None:
            self.scrap_log = set()
            self._cur.execute("SELECT scrap_id FROM tbl_scrap_log WHERE timestamp > DATE_ADD(NOW(), INTERVAL -24 HOUR)")
            res = self._cur.fetchone()
            while res:
                self.scrap_log.add(res[0])
                res = self._cur.fetchone()

        return str(scrap_id) in self.scrap_log



    @property
    def url(self):
        return self.url_template % (self.postcode, self.page_num)

    def write_tag_db(self, soup_tag):
        assert isinstance(soup_tag, element.Tag)
        html_text = unicode(soup_tag)
        ad_text = unicode(soup_tag.get_text()).strip()
        hash_id = hash(ad_text)

        self._cur.execute("SELECT hash_id FROM tbl_html_text WHERE hash_id = %s", (hash_id,))
        rs = self._cur.fetchall()
        date = str(datetime.datetime.now())
        if len(rs) > 0:
            sql = "UPDATE tbl_html_text SET last_seen_date = CURRENT_TIMESTAMP WHERE hash_id = %s"
            self._cur.execute(sql, (hash_id,))
            self._conn.commit()
            return False
        else:
            sql = "INSERT INTO tbl_html_text (hash_id, html_text, url, ad_text)" \
                  " VALUES (%s, %s, %s, %s)"
            val = (hash_id, html_text, self.url, ad_text)
            self._cur.execute(sql, val)
            self._conn.commit()
            return True

    def read_one_page(self):
        """
        :return:
         soup tags in list
        """
        r = requests.get(self.url)
        html = r.content
        self.soup = BeautifulSoup(html, "lxml")
        return self.soup.find_all("article")


if __name__ == "__main__":
    scraper = BaseScraper()
    scraper.test_db()
    step = 1
    last_saved_page = 1
    err_happens = 0
    tic = time.time()

    with open("./data/post_code_data.csv", 'r') as f:
        postcodes = []
        for line in f:
            postcode = line.split(",")[0]
            if postcode.isdigit() and (postcode not in postcodes):
                postcodes.append(postcode)
    # try:
    #     conn = db_connector()
    #     cur = conn.cursor()
    #     cur.execute("""SELECT DISTINCT scrap_id FROM tbl_scrap_log WHERE timestamp > %s limit 10""",
    #                 (str(datetime.datetime.now() - datetime.timedelta(days=1)),))
    #
    #     scraped_postcode = set()
    #     r = cur.fetchall()
    #
    #     tac = time.time()
    #     print("(" + str(tac-tic) + " seconds)")
    # finally:
    #     conn.close()

    # max_pn = 0
    # for pn in range(len(postcodes)):
    #     if postcodes[pn] in scraped_postcode:
    #         max_pn = pn

    for pn in range(len(postcodes)):
        postcode = postcodes[pn]
        scraper.postcode = postcode
        scraper.page_num = 1
        print('\n', "*" * 40, end='')
        print("POSTCODE:", postcode, "(%d/%d)" % (pn, len(postcodes)), "*" * 40)
        if scraper.has_scraped(postcode):
            print("------------skipping this postcode.-------------")
            continue

        time.sleep(2)
        saved_tags_this_postcode = 0

        while True:
            try:
                print('\n', "-"*80)
                print(datetime.datetime.now())
                print(scraper.url)
                print("loading web page...", end='')

                tic = time.time()
                tags = scraper.read_one_page()
                toc = time.time()
                print("(%f seconds used)" % (toc - tic))

                if len(tags) == 0:
                    print("no property found.")
                    break

                assert isinstance(tags[0], element.Tag)
                print("%d properties are found, saving to database..." % len(tags))
                i = 0
                for tag in tags:
                    if scraper.write_tag_db(tag):
                        i += 1
                        saved_tags_this_postcode += 1
                tic = time.time()
                print("%d are saved. (%f seconds used)" % (i, (tic - toc)))

                if len(tags) < 20:
                    found_tag_qty = len(tags) + 20 * (scraper.page_num-1)
                    note_text = "Postcode=%s, Scraped Pages=%d, Ad Found =%d, Saved=%d" % \
                                (str(postcode), scraper.page_num, found_tag_qty, saved_tags_this_postcode)
                    scraper.log_scrap(postcode, note_text)
                    break
                # if i == 0:
                #     scraper.page_num += step
                #     step *= 2
                #     last_saved_page = scraper.page_num
                # else:
                #     if step > 1:
                #         step = 1
                #         scraper.page_num = last_saved_page0
            except Exception as err:
                print(err)
                if err_happens:
                    err_happens += 1
                else:
                    err_happens = 1

                if err_happens > 10:
                    raise err
                time.sleep(5)
            else:
                err_happens = 0
                scraper.page_num += 1
                if scraper.page_num % 10 == 0:
                    time.sleep(2)





