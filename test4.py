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

with sqlite3.connect('tmp.db') as conn:
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


def scrape_product(base_url='https://www.jbhifi.com.au/products/nikon-af-s-dx-nikkor-35mm-f-1-8g-lens'):
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
    # Flatten the singleton (I hope) "variants" down.
    assert len(meta_dict['variants']) == 1
    meta_dict.update(meta_dict['variants'][0])
    del meta_dict['variants']
    with sqlite3.connect('tmp.db') as conn:
        conn.execute(
            """
            REPLACE INTO SKUs
            (SKU, type, make, model, price)
            VALUES
            (:sku, :type, :vendor, :name, :price)""",
            meta_dict)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    scrape_product()
    walk_sitemap()
