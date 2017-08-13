import re


value_range = (100000, 100000000)  # price range from $ 100 K ~ $ 10 Mil

pattern = re.compile(r"(?<=\$)[\s\d,]+\.?\d+\s*(?:mil|m(?=\W)|m$|k(?=\W)|k$)?|"
                     r"\d+[\d\s,]+000\s*(?:mil|m(?=\W)|m$|k(?=\W)|k$)?|"
                     r"\d+[\d\s,]+\.?[\d\s]*(?:mil|m(?=\W)|m$|k(?=\W)|k$)", re.IGNORECASE)


def extract_num(text):
    t = ""
    for c in text:
        if c.isdigit() or c == ".":
            t += c
    ts = t.split(".")
    if len(ts) > 2:
        t = ".".join(ts[:2])
    if t:
        return float(t)
    else:
        return 0.0


def get_single_price_value(single_price_text):
    assert isinstance(single_price_text, basestring)
    t = single_price_text.lower()
    val = extract_num(t)
    if val:
        if "k" in t:
            val *= 1000
        elif "m" in t:
            val *= 1000000
    return val


def parse_price_text(price_text):
    """
    
    :param price_text: 
    :return: price value in float, or scenario in string,
    """
    assert isinstance(price_text, basestring)
    match = pattern.findall(price_text)
    # cat 0: no digit at all
    if not match:
        # if any(i.isdigit() for i in price_text):
        #     print "cat 0:", price_text
        return "No Match."
    # cat 1: single number
    elif len(match) == 1:
        value = get_single_price_value(match[0])
        if value:
            if value_range[0] <= int(value) <= value_range[1]:
                return value
            else:
                return "Single Match, but value not in range."
        else:
            return "Single match, but none value."

    # cat 2: two numbers
    elif len(match) == 2:
        value1 = get_single_price_value(match[0])
        value2 = get_single_price_value(match[1])
        if value_range[0] <= int(value1) <= value_range[1]:
            if value_range[0] <= int(value2) <= value_range[1]:
                return (value1+value2)/2
            else:
                return value1
        elif value_range[0] <= int(value2) <= value_range[1]:
            return value2
        else:
            return "Match two, but value not in range."
    else:
        return "Multiple Match."


if __name__ == "__main__":
    import sqlite3
    with sqlite3.connect("./data/database.db") as conn:
        cur = conn.cursor()
        cur.execute("select price_text from tbl_property_ad  limit 10000 ")
        line = cur.fetchone()

        while line:
            price_text = line[0]
            price = rt(price_text)
            if not isinstance(price, float):
                if "No Match" not in price:
                    print price, price_text
            line = cur.fetchone()
        pass

