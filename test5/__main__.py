#!/usr/bin/python3
import dataclasses
import pathlib

import arrow
import scrapy.crawler
import scrapy
import scrapy.spiders

# In scrapy terminology,
#   a "project" is a directory containing scrapy.cfg and a "crawler".
#   a "crawler" is a python module that contains multiple "spiders" (& optionally more)
#   a "spider"  is a python class that does the ACTUAL SCRAPING.
#   an "item"   is a python object representing one scraped "thing" - e.g. on asos.com, a dress.

class DigiDirectSpider(scrapy.spiders.SitemapSpider):
    name = 'DigiDirect'
    sitemap_urls = ['https://digidirect.com.au/sitemap.xml']
    sitemap_rules = [
        (r'/', 'parse_product'),
        (r'/brands/', 'nop'),
    ]
    def nop(self):
        pass
    def parse_product(self, response):
        # if we get a 403 or 426 or similar, just stop everything right now!
        if response.status not in (200, 404):
            self.crawler.stop()
        yield Product(
            sku=int(response.xpath('//*[@itemprop="sku"]/text()').get()),
            price=int(100 * float(response.xpath('//*[@itemprop="price"]/@content').get())),  # 1$ = 100
            model=response.xpath('//*[@itemprop="name"]/text()').get(),
            make='FIXME')

    # Skip any URLs that haven't changed since we last scraped.
    def sitemap_filter(self, entries):
        for entry in entries:
            try:
                if self.last_complete_scrape_datetime() <= arrow.get(entry['lastmod']):
                    yield entry
            except KeyError:
                # no lastmod?  Scrape it
                yield entry

    # FIXME: actually store this in the database somewhere.
    #        for now just fake it out and assume we succeeded at least once a week
    @classmethod
    def last_complete_scrape_datetime(self):
        global timestamp_path   # FIXME: YUK
        if timestamp_path.exists():
            with timestamp_path.open() as f:
                return arrow.get(f.read().strip())
        else:
            return arrow.get('1970-01-01')  # "forever" ago


@dataclasses.dataclass
class Product:
    sku: int
    make: str
    model: str
    price: int



# FIXME: there is almost certainly a built-in thing for this within scrapy... somewhere.
timestamp_path = pathlib.Path('test5.timestamp')  # FIXME: this belongs in an actual database
timestamp_now  = arrow.now()     # when THIS run STARTED

# One "CrawlerProcess" runs one-or-more "spiders" concurrently.
# e.g. scraping both Asos.com and Topshop.com at the same time.
proc = scrapy.crawler.CrawlerProcess(
    settings={
        # Actually check the TLS cert.  Like, at all.
        'DOWNLOADER_CLIENTCONTEXTFACTORY':
        'scrapy.core.downloader.contextfactory.BrowserLikeContextFactory',
        # Write shit out to a CSV for now, since ICBF patching in sqlite3 support yet.
        'FEEDS': { pathlib.Path('test5.csv'): {'format': 'csv'}, },
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
        # # ---------- Rate limiting stuff ----------
        # 'DOWNLOAD_DELAY': 0.25,  # at most 4 requests per second (on average)
        # 'AUTOTHROTTLE_ENABLED': True,
        # #'AUTOTHROTTLE_START_DELAY': 10,
        # 'AUTOTHROTTLE_TARGET_CONCURRENCY': 2,
    }
)
proc.crawl(crawler_or_spidercls=DigiDirectSpider)
proc.start()

# Update the "last successful scrape" timestamp, so next run can skip old stuff.
with timestamp_path.open(mode='w') as f:
    print(timestamp_now, file=f)
