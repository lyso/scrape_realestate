# coding=utf-8
import sqlite3
import nose.tools

from scraper import BaseScraper
import bs4

ae = nose.tools.assert_equal

scraper = BaseScraper()
BaseScraper.db = "./test/scraper_dumps.db"


def test_db():
    with sqlite3.connect(BaseScraper.db) as conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE if EXISTS tbl_html_text")
        conn.commit()
    scraper.test_db()


def test_read_one_page():
    tags = scraper.read_one_page()
    assert isinstance(tags[0], bs4.element.Tag)
    for tag in tags:
        scraper.write_tag_db(tag)


def test_update_db():
    with sqlite3.connect("./test/scraper_dumps.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT hash_id, html_text, ad_text FROM  tbl_html_text")
        rs = cur.fetchall()
        for row in rs:
            if not row[2]:
                soup = bs4.BeautifulSoup(row[1], "lxml")
                ad_text = soup.get_text()
                cur.execute("UPDATE tbl_html_text SET ad_text=? WHERE hash_id = ?", (ad_text, row[0]))

#
# def test_open_csv():
#     with open("./data/post_code_data.csv", 'r') as f:
#         postcodes = []
#         for line in f:
#             postcode = line.split(",")[0]
#             if postcode.isdigit():
#                 postcodes.append(postcode)
#         else:
#             print postcodes

