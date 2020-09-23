#!/usr/bin/python3
import scrapy.crawler
import test3.spider

# In scrapy terminology,
#   a "project" is a directory containing scrapy.cfg and a "crawler".
#   a "crawler" is a python module that contains multiple "spiders" (& optionally more)
#   a "spider"  is a python module that does the ACTUAL SCRAPING.

proc = scrapy.crawler.CrawlerProcess()
proc.crawl(crawler_or_spidercls=test3.spider.X)
proc.start()
