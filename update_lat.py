import sqlite3
import time
from datetime import datetime
import json

from geopy import GoogleV3

# import parser

now = str(datetime.now())
today = now[:10]
db = "./data/database.db"
saved_addresses = set()


def saved_address_num(address_text):
    """
    get the number of saved address records in database
    :param address_text: 
    :return: 
        None
    """
    if not saved_addresses:
        with sqlite3.connect(db) as conn:
            cur = conn.cursor()
            try:
                cur.execute('select address_text from tbl_address_lat')
            except sqlite3.OperationalError as err:
                if err.args[0] == "no such table: tbl_address_lat":
                    cur.execute("CREATE TABLE `tbl_address_lat` ("
                                "`id`	INTEGER PRIMARY KEY AUTOINCREMENT, "
                                "`address_text`	TEXT NOT NULL, "
                                "`lat`	REAL, "
                                "`long`	REAL,"
                                "`api_string` TEXT, "
                                "`create_date` TEXT);")
                    conn.commit()
                    return None
                else:
                    raise err
            res = cur.fetchone()
            while res:
                saved_addresses.add(res[0])
                res = cur.fetchone()

    if address_text in saved_addresses:
        with sqlite3.connect(db) as conn:
            cur = conn.cursor()
            cur.execute('select api_string from tbl_address_lat WHERE address_text = ?', (address_text,))
            rs = cur.fetchone()
            if rs:
                api_string = rs[0]
                if api_string:
                    assert isinstance(api_string, basestring)
                    dict_rs = json.loads(api_string)
                    return dict_rs
                else:  # found this address but google could not recognize it
                    return {}
            else:  # not found this address in db
                return None
    else:  # not found this address in db
        return None


def update_lat(max_row):
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT address, id, state, postcode FROM tbl_property_ad "
                    "WHERE lat is NULL and state = 'NSW' AND type = 'residential' LIMIT ?",
                    (max_row,))
        rs = cur.fetchall()

    max_query_number = 2500
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM tbl_address_lat WHERE SUBSTR(create_date,1,10) = ?", (today,))
        today_query_number = cur.fetchone()[0]

    for property_ in rs:
        address_text = property_[0]
        property_id = property_[1]
        state = property_[2]
        postcode = property_[3]
        normalized_address = ""
        lat_ = None
        lng_ = None

        if address_text:
            dict_geo = saved_address_num(address_text)
            if isinstance(dict_geo, dict):
                try:
                    lat_ = dict_geo['geometry']['location']['lat']
                    lng_ = dict_geo['geometry']['location']['lng']
                except KeyError:
                    lat_ = None
                    lng_ = None

                    # set saved address to suburb
                    address_text = state + " " + str(postcode)
                    normalized_address = address_text
                    dict_geo = saved_address_num(address_text)
                    if isinstance(dict_geo, dict):
                        try:
                            lat_ = dict_geo['geometry']['location']['lat']
                            lng_ = dict_geo['geometry']['location']['lng']
                        except KeyError:
                            lat_ = None
                            lng_ = None

            if not lat_:
                # if not found in db, go for geopy
                if today_query_number < max_query_number:
                    geo = GoogleV3(api_key="AIzaSyALRQvXf8IwBIU6HI8btqv4TtSMarfm-98", timeout=20)
                    location = geo.geocode(address_text)
                    time.sleep(0.1)
                    today_query_number += 1
                    now_ = str(datetime.now())
                    print "Geocode quotation:", today_query_number, ":", address_text

                    if location:
                        lat_ = location.latitude
                        lng_ = location.longitude
                        if not normalized_address:
                            normalized_address = location.address
                        cur.execute("INSERT INTO tbl_address_lat (address_text, lat, long, api_string, create_date) "
                                    "VALUES (?, ?, ?, ?, ?)",
                                    (address_text, lat_, lng_, json.dumps(location.raw), now_))
                        conn.commit()
                    else:
                        cur.execute("INSERT INTO tbl_address_lat (address_text, lat, long, api_string, create_date) "
                                    "VALUES (?, ?, ?, ?, ?)",
                                    (address_text, None, None, None, now_))
                        conn.commit()
                        lat_ = 0
                        lng_ = 0

                else:
                    break

            # update back to tbl_property_ad
            with sqlite3.connect(db) as conn:
                cur = conn.cursor()
                cur.execute("UPDATE tbl_property_ad SET lat = ?, long = ?, address_nomalized = ?"
                            " WHERE id = ?",
                            (lat_, lng_, address_text, property_id))
                conn.commit()


if __name__ == "__main__":
    update_lat(10000)


