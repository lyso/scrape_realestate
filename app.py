# coding:utf-8

import requests
from bs4 import BeautifulSoup

domain = "www.realestate.com.au"
url_template = "http://www.realestate.com.au/buy/list-%s"
page_num = 1


def get_list_page_soup():
    url = url_template % page_num
    r = requests.get(url)
    html = r.content
    soup = BeautifulSoup(html)
    return soup


def parse_property_soup():
    """
    parse the soup of property get from list page, do not go inside the detailed page
    :return: an PropertyOnSale object
    """
    pass


def parse_list_page_soup(list_page_soup, parse_property):
    assert isinstance(list_page_soup, BeautifulSoup)

    for article in list_page_soup.find_all("article"):
        property_ = parse_property(article)
        assert isinstance(property_, PropertyOnSale)


class PropertyOnSale(object):
    db = "./data/database.db"

    def __init__(self):
        self.data = {}
        # self.price_text = ""
        # self.address = ""
        # self.rooms = [0, 0, 0]
        # self.price = 0
        # self.agent_name = ""
        # self.agent_company = ""
        # self.raw_list_text = ""
        # self.hash_id = 0
        # self.sale_type = ""

    def create_property_tbl(self):
        import sqlite3
        sql = "create table if not exists tbl_property " \
              "( `hash_id` INTEGER NOT NULL, " \
              "`id` INTEGER PRIMARY KEY AUTOINCREMENT, " \
              "`address` TEXT NOT NULL, " \
              "`price` INTEGER, " \
              "`price_text` TEXT, " \
              "`agent_name` TEXT, " \
              "`agent_company` TEXT, " \
              "`raw_list_text` TEXT, " \
              "`rooms` TEXT, " \
              "`type` TEXT," \
              "`subtype` TEXT )"
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute(sql)

    def data_tuples(self):
        """
        take the self.data and change to (head, data) pair
        :return: 
        ([h1, h2,...hn], [d1, d2,..dn])
        """

        t1 = [h for h in self.data]
        t2 = []
        for h in t1:
            val = self.data[h]
            if isinstance(val, basestring):
                t2.append(val)
            else:
                t2.append(unicode(val))
        t2 = [self.data[d] for d in self.data]

        return t1, t2

    def update_db(self):
        """
        
        :return: 
            None: if same record exists
            
        """
        import sqlite3
        select_sql = "SELECT hash_id AS ct FROM tbl_property WHERE hash_id = ?"
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute(select_sql, (self.hash_id, ))
            rs = cur.fetchall()
        if len(rs) > 0:
            # same record exists
            return None
        else:
            # not found same record
            dt = self.data_tuples()
            head_str = ", ".join(dt[0])
            question_mark_str = ", ".join(tuple("?"*len(dt[0])))

            insert_sql = "INSERT INTO tbl_property " \
                         "(" + head_str + ")" \
                         "VALUES (" + question_mark_str + ") "
            with sqlite3.connect(self.db) as conn:
                cur = conn.cursor()
                vals = (self.hash_id, self.address, self.price,
                        self.price_text, self.agent_name, self.agent_company,
                        self.raw_list_text, ",".join([str(i) for i in self.rooms]), "Sale",
                        self.sale_type)
                cur.execute(insert_sql, vals)
                conn.commit()











if __name__ == "__main__":
    soup = get_list_page_soup()
    print soup.prettify()

