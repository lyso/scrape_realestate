import sqlite3
import re


def extract_num(text):
    t = ""
    for c in text:
        if c.isdigit() or c == ".":
            t += c
    if t:
        return float(t)
    else:
        return None


def rt(price_text):
    assert isinstance(price_text, basestring)
    pattern = re.compile(r"\$\s?[\s\d,]+\.?[\s\d,]*|[\d,]+000")
    match = pattern.findall(price_text)
    # cat 0: no digit at all
    if not match:
        # if any(i.isdigit() for i in price_text):
        #     print "cat 0:", price_text
        pass
    # cat 1: single number
    elif len(match) == 1:
        # cat 1.1 per 1$
        # cat 1.2 per 1K$
        pattern1_1 = re.compile(r"(\$\s?[\s\d,]+\.?[\s\d,]*|[\d,]+000)\s?[Kk]")
        match1_1 = pattern1_1.search(price_text)
        # cat 1.3 per 1M$
        pattern1_2 = re.compile(r"(\$\s?[\s\d,]+\.?[\s\d,]*|[\d,]+000)\s?[mM]")
        match1_2 = pattern1_2.search(price_text)

        if match1_1:  # k
            price = extract_num(match1_1.group(0))
            if price:
                if 100000.0 > price > 100:
                    price = price*1000
        elif match1_2:  # million
            price = extract_num(match1_2.group(0))
            if price:
                if 100.0 > price > 0.1:
                    price = price*1000000
        else:
            price = extract_num(match[0])
            pass

    # cat 2: two numbers
    elif len(match) == 2:
        price1 = extract_num(match[0])
        if price1 < 10000:
            print "cat 2:", price_text, price1

        pass
    else:
        print "mismatch:", price_text

    pass


with sqlite3.connect("./data/database.db") as conn:
    cur = conn.cursor()
    cur.execute("select price_text from tbl_property_ad  limit 10000 ")
    rs = cur.fetchall()

for line in rs:
    price_text = line[0]
    rt(price_text)
pass

