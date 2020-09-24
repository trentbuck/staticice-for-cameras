#!/usr/bin/python3

# scrapy has SO MUCH middleware and OO, I was getting frustrated.
# Let's go back to doing it the way I normally do.

import argparse
import contextlib
import json
import os
import pprint
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.parse

import requests
import lxml.html

sess = requests.Session()
sess.headers['User-Agent'] = 'Mozilla/5.0'
def GET(url):
    resp = sess.get(url)
    resp.raise_for_status()
    return resp
def XPATH(url, xpath):
    return lxml.html.fromstring(GET(url).content).xpath(xpath)
def DL(url, path):
    resp = GET(url)
    with open(path, mode='wb') as f:  # binary because probably a JPEG
        f.write(resp.content)
def mystrip(s: str, prefix='', suffix='') -> str:
    if prefix:
        assert s.startswith(prefix)
        s = s[len(prefix):]
    if suffix:
        assert s.endswith(suffix)
        s = s[:-len(suffix)]
    return s

# FIXME: don't just dangle the connection indefinitely!
# FIXME: isolation_level=None means AUTOCOMMIT instead of implicit transactions -- yukky!
conn = sqlite3.connect('test4.db', isolation_level=None)
conn.execute('PRAGMA journal_mode = WAL')
conn.execute("""
CREATE TABLE IF NOT EXISTS SKUs (
SKU   INTEGER PRIMARY KEY,
type  TEXT NOT NULL,
make  TEXT NOT NULL,
model TEXT NOT NULL,
price INTEGER NOT NULL    ---- in AUD cents, e.g. 12345 means A$123.45
)
""")


def walk_sitemap(base_url='https://jbhifi.com.au/sitemap.xml'):
    # Ref. https://en.wikipedia.org/wiki/Sitemaps
    print(base_url, flush=True)  # DEBUGGING
    resp = sess.get(base_url)
    resp.raise_for_status()
    etree = lxml.html.fromstring(resp.content)
    for product_url in etree.xpath('//urlset/url/loc/text()'):
        # FIXME: only scrape the product if the content has changed
        # since our last SUCCESSFUL (full) scrape of this site.
        if product_url.startswith('https://www.jbhifi.com.au/products/'):
            scrape_product(product_url)
    for child_sitemap_url in etree.xpath('//sitemapindex/sitemap/loc/text()'):
        walk_sitemap(child_sitemap_url)


# It is slow (time expensive) to re-download pages we've seen.
# It is big (space expensive) to remember what we've seen, but
# that is an overall win.
# If the URLs had the SKUs in them, this would be MUCH cheaper on the disk.
# FIXME: just putting (a tuned) squid in front would probably work better!
# FIXME: possibly remember WHEN we last looked, and remember that?
def scrape_product(base_url):
    conn.execute('CREATE TABLE IF NOT EXISTS BTDT (url TEXT PRIMARY KEY)')
    already_fetched = bool(conn.execute('SELECT 1 FROM BTDT WHERE url = ?', (base_url,)).fetchall())
    if not already_fetched:
        _scrape_product(base_url)
        conn.execute('INSERT INTO BTDT (url) VALUES (?)', (base_url,))


def _scrape_product(base_url):
    print(base_url, flush=True)  # DEBUGGING
    resp = sess.get(base_url)
    resp.raise_for_status()
    etree = lxml.html.fromstring(resp.content)
    meta_line, = [
        mystrip(line, prefix='var meta = ', suffix=';')
        for s in etree.xpath('//script/text()')
        for line in s.splitlines()
        if line.startswith('var meta = ')]
    meta_dict = json.loads(meta_line)['product']
    # GIVE UP early if this product is definitely not camera-related.
    # e.g. definitely not "CAMERAS", but also not "ACCESSORIES", "VISUAL", &c??
    if meta_dict['type'] in shit_types:
        return None
    # Flatten the singleton (I hope) "variants" down.
    assert len(meta_dict['variants']) == 1
    meta_dict.update(meta_dict['variants'][0])
    del meta_dict['variants']
    conn.execute(
        """
        INSERT INTO SKUs
        (SKU, type, make, model, price)
        VALUES
        (:sku, :type, :vendor, :name, :price)""",
        meta_dict)


shit_types = ('MUSIC', 'MOVIES', 'SMALL APPLIANCES', 'WHITEGOODS', 'GAMES SOFTWARE', 'GAMES HARDWARE')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    scrape_product('https://www.jbhifi.com.au/products/nikon-af-s-dx-nikkor-35mm-f-1-8g-lens')
    walk_sitemap()
