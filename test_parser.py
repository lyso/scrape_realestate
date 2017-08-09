# coding=utf-8
import sqlite3
import nose.tools
import bs4

import parser

ae = nose.tools.assert_equal


def test_ad_type():
    db = "./test/scraper_dumps.db"
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT html_text FROM tbl_html_text LIMIT 5000")
        rs = cur.fetchall()

    ad_types = []
    for row in rs:
        assert isinstance(row, tuple)
        soup = bs4.BeautifulSoup(row[0], "html.parser")
        try:
            ad_type = soup.article['class']
        except KeyError:
            pass
        else:
            ad_type = " ".join(ad_type)
            if ad_type not in ad_types:
                ad_types.append(ad_type)
                print ad_type


if __name__ == "__main__":
    with sqlite3.connect("./data/scraper_dumps.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT url FROM tbl_html_text")
        res = cur.fetchall()

    postcodes = {}
    for url in res:
        url = url[0]
        if isinstance(url, basestring):
            try:
                postcode = url.split("in-")[1]
                postcode = postcode.split("/")[0]
                if postcode.isdigit():
                    if postcode in postcodes:
                        postcodes[postcode] += 1
                    else:
                        postcodes[postcode] = 1
            except:
                pass
    with open("postcode result.txt", 'w') as f:
        for postcode in postcodes:
            f.write(str(postcode) + ',' + str(postcodes[postcode]) + "\n")


