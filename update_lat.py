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
    assert isinstance(address_text, basestring)
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        try:
            cur.execute('select api_string from tbl_address_lat WHERE address_text = ?', (address_text,))
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


def update_lat(max_row):

    max_query_number = 2450
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM tbl_address_lat WHERE create_date > date('now')")
        today_query_number = cur.fetchone()[0]

    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur_update = conn.cursor()
        cur.execute("SELECT address, id, state, postcode FROM tbl_property_ad "
                    "WHERE state = 'NSW' AND type = 'residential'")
                    # "WHERE lat is NULL and state = 'NSW' AND type = 'residential' LIMIT ?",
                    # (max_row,))
        # rs = cur.fetchall()
        # it = iter(rs)
        # property_ = it.next()

        retry_num = 0
        while True:
            property_ = cur.fetchone()
            if not property_:
                break
            try:
                address_text = property_[0]
                property_id = property_[1]
                state = property_[2]
                postcode = property_[3]
                normalized_address = ""
                lat_ = None
                lng_ = None

                if address_text:
                    ADDRESS_TEXT = address_text.strip().upper()
                    dict_geo = saved_address_num(ADDRESS_TEXT)
                    if isinstance(dict_geo, dict):
                        try:
                            lat_ = dict_geo['geometry']['location']['lat']
                            lng_ = dict_geo['geometry']['location']['lng']
                            normalized_address = dict_geo['formatted_address']
                        except KeyError:  # empty dict_geo, so go for suburb location

                            lat_ = None
                            lng_ = None

                            # set saved address to suburb
                            ADDRESS_TEXT = state + " " + str(postcode)
                            normalized_address = ADDRESS_TEXT
                            dict_geo = saved_address_num(ADDRESS_TEXT)
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
                            location = geo.geocode(ADDRESS_TEXT)
                            time.sleep(0.2)
                            today_query_number += 1
                            now_ = str(datetime.now())
                            print "Geocode quotation:", today_query_number, ":", address_text

                            if location:
                                lat_ = location.latitude
                                lng_ = location.longitude
                                if not normalized_address:
                                    normalized_address = location.address
                                cur_update.execute("INSERT INTO tbl_address_lat (address_text, lat, long, api_string, create_date) "
                                                   "VALUES (?, ?, ?, ?, ?)",
                                                   (ADDRESS_TEXT, lat_, lng_, json.dumps(location.raw), now_))
                                conn.commit()
                            else:
                                cur_update.execute("INSERT INTO tbl_address_lat (address_text, lat, long, api_string, create_date) "
                                                   "VALUES (?, ?, ?, ?, ?)",
                                                   (ADDRESS_TEXT, None, None, None, now_))
                                conn.commit()
                                lat_ = 0
                                lng_ = 0

                        else:
                            continue

                    # update back to tbl_property_ad
                    cur_update.execute("UPDATE tbl_property_ad SET lat = ?, long = ?, address_normalized = ?"
                                       "WHERE id =  ?",
                                       (lat_, lng_, normalized_address, property_id))
                    conn.commit()
            except Exception as err:
                print err
                retry_num += 1
                if ((retry_num > 5) and (today_query_number > max_query_number-200)) or (retry_num > 15):
                    print input("Enter to exit:")
                    break
                time.sleep(60)
            else:
                retry_num = 0

if __name__ == "__main__":
    update_lat(10000000000)


