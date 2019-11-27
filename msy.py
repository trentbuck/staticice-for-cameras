#!/usr/bin/python3
import argparse
import csv
import datetime
import os
import sys
import sqlite3

import lxml.etree
import lxml.html
import requests


def main():
    parser = argparse.ArgumentParser(
        description='The WINWORD.EXE-based MSY part list rends slowly. Rip it to a CSV.')
    _ = parser.parse_args()     # we don't actually use any args.

    ## This stopped working 1 Aug 2019, because msy now requires https.
    #data = lxml.html.parse('http://msy.com.au/Parts/PARTS_W.HTM')
    ## Therefore, lxml can't do the downloading all on its own; we have to do it by hand.
    ## UPDATE: ACTUALLY NO, THAT FAILS AS WELL, THE PART LIST IS JUST GONE????
    #resp = requests.get('https://msy.com.au/Parts/PARTS_W.HTM')
    #resp.raise_for_status()
    #data = lxml.html.fromstring(resp.text)
    ## This is the "new" URL?  It's 4MB long (instead of 0.5MB long), and it has all the MSO namespace crap from WINWORD still in it.  PARTS_W.HTM seems to be working for now (1 Aug 2019)
    #    resp = requests.get('https://cdn.msy.com.au/Parts/msy.htm')
    resp = requests.get('https://old.msy.com.au/Parts/PARTS_W.HTM')
    resp.raise_for_status()
    data = lxml.html.fromstring(resp.text)

    acc = set()
    os.chdir(os.path.expanduser('~/Preferences/msy-data'))
    with open('msy.{}.err'.format(datetime.date.today()), 'w') as f:
        for row in data.xpath('//table[2]/tr'):
            try:
                sku, price = row.xpath('td/p/span/text()')
            except ValueError:
                print('IGNORING ROW WITH WRONG NUMBER OF CELLS:',
                      lxml.etree.tostring(row, encoding=str),
                      file=sys.stderr, flush=True)
                continue
            sku = ' '.join(sku.split())  # flatten whitespace
            sku = sku.replace('"','in')  # e.g. 29" LCD ⇒ 29in LCD
            sku = sku.replace("''",'in')  # e.g. 29'' LCD ⇒ 29in LCD
            try:
                price = int(price.strip())
            except ValueError:
                print(price, sku, file=f)  # log errors
            else:
                if price == 9999:
                    print(price, '(fake price)', sku, file=f)  # log errors
                    continue
                if price % 10 == 9:
                    price += 1      # reverse deceptive pricing
                acc.add((price, sku))
    acc = sorted(acc, key=fuck_youₚython)
    path = 'msy.{}.csv'.format(datetime.date.today())
    with open(path, 'w') as f:
        g = csv.writer(f, dialect='excel-tab')
        g.writerows(
            ('{:5}$'.format(price), sku)
            for price, sku in acc)

    legacy_path = os.path.expanduser('~/Desktop/msy.txt')
    if os.path.exists(legacy_path):
        os.remove(legacy_path)
    os.link(path, legacy_path)

    tell_database(acc)


# Python won't let me use (λ: x, y: -x, y), because its λ is crippled.
def fuck_youₚython(x):
    (price, sku) = x
    return -price, sku


def tell_database_FIRST_DRAFT(rows):
    with sqlite3.connect('msy.db') as conn:
        conn.execute('PRAGMA journal_mode = wal')
        conn.execute('CREATE TABLE IF NOT EXISTS SKUs (SKU TEXT PRIMARY KEY)')
        conn.execute('CREATE TABLE IF NOT EXISTS dates (date TEXT PRIMARY KEY)')
        conn.execute('CREATE TABLE IF NOT EXISTS prices ('
                     'price INTEGER,'
                     'SKU REFERENCES SKUs,'
                     'date REFERENCES dates,'
                     'PRIMARY KEY (SKU, date))')
        conn.execute('INSERT INTO dates VALUES (date()) ON CONFLICT DO NOTHING')
        conn.executemany('INSERT INTO SKUs VALUES (?) ON CONFLICT DO NOTHING',
                         ((sku,) for price, sku in rows))
        conn.executemany('INSERT INTO prices VALUES (?, ?, date()) ON CONFLICT DO NOTHING',
                         rows)


def tell_database(rows):
    with sqlite3.connect('msy.db') as conn:
        conn.execute('PRAGMA journal_mode = wal')
        conn.execute('CREATE TABLE IF NOT EXISTS SKUs (SKU_id INTEGER PRIMARY KEY, SKU TEXT UNIQUE NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS prices ('
                     'price INTEGER,'
                     'SKU_id REFERENCES SKUs,'
                     'date_ordinal INTEGER NOT NULL,'
                     'PRIMARY KEY (SKU_id, date_ordinal))')
        o = datetime.date.today().toordinal()  # 0001-01-01 = 1, 0001-01-02 = 2, &c.
        conn.executemany('INSERT INTO SKUs (SKU) VALUES (?)'
                         ' ON CONFLICT DO NOTHING',
                         ((sku,) for price, sku in rows))
        conn.executemany('INSERT INTO prices (price, SKU_id, date_ordinal)'
                         ' VALUES (?, (SELECT SKU_id FROM SKUs WHERE SKU = ?), ?)'
                         ' ON CONFLICT DO NOTHING',
                         ((price, sku, o) for price, sku in rows))

        # date_ordinal to date:
        #  sqlite> select date('0001-01-01', 736928 || ' days', '-1 days');


if __name__ == '__main__':
    main()
