# coding:utf-8

import requests
import sqlite3
import datetime
import time
from bs4 import BeautifulSoup, element


class BaseScraper(object):
    db = "./data/scraper_dumps.db"

    def __init__(self):
        self.domain = "www.realestate.com.au"
        self.url_template = "http://www.realestate.com.au/buy/in-%s/list-%s?includeSurrounding=false"
        self.page_num = 1
        self.postcode = 2077
        self.soup = None
        self._conn = sqlite3.connect(self.db)
        self._cur = self._conn.cursor()
        self.write_queue_len = 0

    def test_db(self):
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute("create table if not exists tbl_html_text"
                        "(`hash_id` INTEGER NOT NULL, "
                        "`html_text` TEXT NOT NULL, "
                        "`create_date` TEXT NOT NULL, "
                        "`url` TEXT NOT NULL, "
                        "`ad_text` TEXT, "
                        "`last_seen_date` TEXT, "
                        "PRIMARY KEY(`hash_id`) )")
            conn.commit()

    @property
    def url(self):
        return self.url_template % (self.postcode, self.page_num)

    def write_tag_db(self, soup_tag):
        assert isinstance(soup_tag, element.Tag)
        html_text = unicode(soup_tag)
        ad_text = unicode(soup_tag.get_text()).strip()
        hash_id = hash(ad_text)

        self._cur.execute("SELECT hash_id FROM tbl_html_text WHERE hash_id = ?", (hash_id,))
        rs = self._cur.fetchall()
        date = str(datetime.datetime.now())
        if len(rs) > 0:
            sql = "UPDATE tbl_html_text SET last_seen_date = ? WHERE hash_id = ?"
            self._cur.execute(sql, (date, hash_id))
            self._conn.commit()
            return False
        else:
            sql = "INSERT INTO tbl_html_text (hash_id, html_text, create_date, url, ad_text, last_seen_date)" \
                  " VALUES (?, ?, ?, ?, ?, ?)"
            val = (hash_id, html_text, date, self.url, ad_text, date)
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

    print "pre loading ...",
    tic = time.time()

    with open("./data/post_code_data.csv", 'r') as f:
        postcodes = []
        for line in f:
            postcode = line.split(",")[0]
            if postcode.isdigit() and (postcode not in postcodes):
                postcodes.append(postcode)
    with sqlite3.connect(scraper.db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT url FROM tbl_html_text "
                    "WHERE url like '%list-1?includeSurrounding=false' "
                    "AND last_seen_date > '" + str(datetime.datetime.now() - datetime.timedelta(hours=5)) + "'")

        scraped_postcode = set()
        r = cur.fetchone()

        while r:
            postcode = r[0]
            postcode = postcode.split("in-")[1]
            postcode = postcode.split("/list-1")[0]
            scraped_postcode.add(postcode)
            r = cur.fetchone()
        tac = time.time()
        print "(" + str(tac-tic) + " seconds)"

    # max_pn = 0
    # for pn in range(len(postcodes)):
    #     if postcodes[pn] in scraped_postcode:
    #         max_pn = pn

    for pn in range(len(postcodes)):
        postcode = postcodes[pn]
        scraper.postcode = postcode
        scraper.page_num = 1
        print '\n', "*" * 40,
        print "POSTCODE:", postcode, "(%d/%d)" % (pn, len(postcodes)), "*" * 40
        if postcode in scraped_postcode:
            print "skip"
            continue

        time.sleep(2)

        while True:
            try:
                print '\n', "-"*80
                print datetime.datetime.now()
                print scraper.url
                print "loading web page...",

                tic = time.time()
                tags = scraper.read_one_page()
                toc = time.time()
                print "(%f seconds used)" % (toc - tic)

                if len(tags) == 0:
                    print "no property found."
                    break

                assert isinstance(tags[0], element.Tag)
                print "%d properties are found, saving to database..." % len(tags)
                i = 0
                for tag in tags:
                    if scraper.write_tag_db(tag):
                        i += 1
                tic = time.time()
                print "%d are saved. (%f seconds used)" % (i, (tic - toc))

                if len(tags) < 20:
                    break
                # if i == 0:
                #     scraper.page_num += step
                #     step *= 2
                #     last_saved_page = scraper.page_num
                # else:
                #     if step > 1:
                #         step = 1
                #         scraper.page_num = last_saved_page0
                err_happens = 0
            except Exception as err:
                if err_happens:
                    err_happens += 1
                else:
                    err_happens = 1

                if err_happens > 10:
                    raise err
                time.sleep(5)
            else:
                scraper.page_num += 1
                if scraper.page_num % 10 == 0:
                    time.sleep(2)





