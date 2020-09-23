#!/usr/bin/python3
import scrapy.crawler
import test3_jb.spider
import test3_jb.sqlite
import scrapy

# In scrapy terminology,
#   a "project" is a directory containing scrapy.cfg and a "crawler".
#   a "crawler" is a python module that contains multiple "spiders" (& optionally more)
#   a "spider"  is a python class that does the ACTUAL SCRAPING.
#   an "item"   is a python object representing one scraped "thing" - e.g. on asos.com, a dress.

class JBHifiSpider(scrapy.Spider):
    name = 'JB Hifi'
    start_urls = ['https://www.jbhifi.com.au/collections/cameras']
    def parse(self, response):
        products_etree, = response.xpath('//*[@id="collection-search-result"]').getall()
        for product_etree in products_etree.xpath('.//@data-product-sku/..'):
            Product(
                sku=product_etree.xpath('./@data-product-sku').get()
                # FUCK, THIS IS ALL AJAX

@dataclasses.dataclass
class Product(scrapy.Item):
    sku: int
    make: str
    model: str
    price: int



# One "CrawlerProcess" runs one-or-more "spiders" concurrently.
# e.g. scraping both Asos.com and Topshop.com at the same time.
proc = scrapy.crawler.CrawlerProcess(
    settings={
        'FEEDS': {
            # output_path: FEED_EXPORTERS key
            'tmp.db': 'sqlite',
        },
        'FEED_EXPORTERS': {
            'sqlite': 'test3_jb.sqlite.SqliteExporter',
        },

        # # FIXME: passing strings to import is bullshit.
        # # Can't we just pass the fucking classes directly?
        # 'ITEM_PIPELINES': {'test3.sqlite.MySqliteWriter': 1},
        # Actually check the TLS cert.  Like, at all.
        'DOWNLOADER_CLIENTCONTEXTFACTORY':
        'scrapy.core.downloader.contextfactory.BrowserLikeContextFactory',
    }
)
proc.crawl(crawler_or_spidercls=JBHifiSpider)
proc.start()

# Bare minimum convert sqlite3 to xlsx
import xlsxwriter
import sqlite3
with xlsxwriter.Workbook('tmp.xlsx') as workbook:
    worksheet = workbook.add_worksheet()
    worksheet.write_row('A1', ['foo', 'bar', 'baz'])  # FIXME: pull headings db
    with sqlite3.connect('tmp.db') as conn:
        for i, row in enumerate(conn.execute('SELECT * FROM quotes').fetchall()):
            worksheet.write_row(f'A{2+i}', row)
