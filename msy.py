#!/usr/bin/python3
import argparse
import csv
import datetime
import os

import lxml.html


def main():
    parser = argparse.ArgumentParser(
        description='The WINWORD.EXE-based MSY part list rends slowly. Rip it to a CSV.')
    _ = parser.parse_args()     # we don't actually use any args.
    data = lxml.html.parse('http://msy.com.au/Parts/PARTS_W.HTM')
    acc = set()
    with open('/home/twb/Preferences/msy-data/msy.{}.err'.format(datetime.date.today()), 'w') as f:
        for row in data.xpath('//table[2]/tr'):
            sku, price = row.xpath('td')
            sku, price = sku.text_content().strip(), price.text_content().strip()
            sku = ' '.join(sku.split())  # flatten whitespace
            sku = sku.replace('"','in')  # e.g. 29" LCD ⇒ 29in LCD
            try:
                price = int(price)
            except ValueError:
                print(price, sku, file=f)  # log errors
            else:
                if price % 10 == 9:
                    price += 1      # reverse deceptive pricing
                acc.add((price, sku))
    path = '/home/twb/Preferences/msy-data/msy.{}.csv'.format(datetime.date.today())
    with open(path, 'w') as f:
        g = csv.writer(f, dialect='excel-tab')
        g.writerows(
            ('{:5}$'.format(price), sku)
            for price, sku in sorted(acc, key=fuck_youₚython))
    os.remove('/home/twb/Desktop/msy.txt')        # legacy path
    os.symlink(path, '/home/twb/Desktop/msy.txt')  # legacy path


# Python won't let me use (λ: x, y: -x, y), because its λ is crippled.
def fuck_youₚython(x):
    (price, sku) = x
    return -price, sku


if __name__ == '__main__':
    main()
