import re

class Price(object):
    value_range = (100000, 100000000)  # 100 K ~ 10 Mil
    def __init__(self, price_text):
        self.raw_text = price_text

    def _recognize_price_text(self,):
        # get first number

        pattern = re.compile(r"\$\s?[\d,]+")
        match = pattern.search(self.raw_text)
        # cat 0: no digit at all
        if not match:
            print "cat 0:", self.raw_text
        # cat 1: single number
        elif len(match) == 1:
            print "cat 1:", self.raw_text
        # cat 2: two numbers
        elif len(match) == 2:
            print "cat 2:", self.raw_text
        else:
            print "mismatch:", self.raw_text

        pass
