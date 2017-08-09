# coding=utf-8
import sqlite3
import nose.tools


from app import PropertyOnSale

ae = nose.tools.assert_equal

dict_val = {"address": "abc",
            "price_text": "$1234",
            "price": 1234,
            "hash_id": hash("address"),
            "raw_list_text": "d;salfj asfafjsa df;sadfj as;",
            'agent_name': 'Simon LiU',
            'agent_company': "Huawei",
            'rooms': [1, 2, 3]}

property_ = PropertyOnSale()


def test_create_db():
    PropertyOnSale.db = "./test/database.db"
    with sqlite3.connect(PropertyOnSale.db) as conn:
        cur = conn.cursor()
        sql = "DROP table if exists tbl_property"
        cur.execute(sql)
        conn.commit()
    property_.create_property_tbl()


def test_update():
    property_.data.update(dict_val)
    assert property_.data == dict_val
    # assert property_.data.address == dict_val['address']
    # assert property_.data.price_text == dict_val['price_text']
    # assert property_.data.hash_id == dict_val['hash_id']
    # assert property_.data.raw_list_text == dict_val['raw_list_text']
    # assert property_.data.agent_name == dict_val['agent_name']
    # assert property_.data.agent_company == dict_val['agent_company']
    # assert property_.data.rooms == dict_val['rooms']


def test_data_tuples():
    res = property_.data_tuples()
    h = res[0]
    d = res[1]
    for i in dict_val:
        assert i in h
        assert dict_val[i] in d


def tes_update_db():
    property_.update_db()

    with sqlite3.connect(PropertyOnSale.db) as conn:
        cur = conn.cursor()
        sql = "SELECT * FROM tbl_property WHERE hash_id = ?"
        cur.execute(sql, (dict_val['hash_id'],))
        headers = [description[0] for description in cur.description]
        rs = cur.fetchall()
    assert len(rs) == 1

    dict_rs = {}
    for i in range(0, len(headers)):
        dict_rs[headers[i]] = rs[0][i]
    dict_rs.pop('id')
    for i in dict_val:
        assert(dict_rs[i] == dict_val[i], 'result value of "' + str(i) + '" is wrong.')

