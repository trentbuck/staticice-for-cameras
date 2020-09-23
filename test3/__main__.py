#!/usr/bin/python3
import scrapy.crawler
import test3.spider
import test3.sqlite

# In scrapy terminology,
#   a "project" is a directory containing scrapy.cfg and a "crawler".
#   a "crawler" is a python module that contains multiple "spiders" (& optionally more)
#   a "spider"  is a python class that does the ACTUAL SCRAPING.
#   an "item"   is a python object representing one scraped "thing" - e.g. on asos.com, a dress.


# One "CrawlerProcess" runs one-or-more "spiders" concurrently.
# e.g. scraping both Asos.com and Topshop.com at the same time.
proc = scrapy.crawler.CrawlerProcess(
    # FIXME: passing strings to import is bullshit.
    # Can't we just pass the fucking classes directly?
    settings={
        'ITEM_PIPELINES': {'test3.sqlite.MySqliteWriter': 1}
    }
)
proc.crawl(crawler_or_spidercls=test3.spider.X)
proc.start()
