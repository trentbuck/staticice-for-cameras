import scrapy
import typing
import pathlib

# FIXME: these don't error:
#   scrapy shell https://example.com/LKJASLDKASJLKDJASD-DOES-NOT-EXIST
#   scrapy shell https://expired.badssl.com/

class X(scrapy.Spider):
    name = 'quotes'
    allowed_domains = ['quotes.toscrape.com']
    start_urls = ['http://quotes.toscrape.com/']

    # Convert the "GET https://quotes.toscrape.com/page/N/"
    # into a list of items (quotes).
    def parse(self, response: scrapy.http.response.html.HtmlResponse) -> typing.Iterator[dict]:
        # FIXME: when xpath has <1 match, .get() cheerfully returns None.
        # FIXME: when xpath has >1 match, .get() cheerfully returns the first.
        # How do I get exceptions for both cases?
        for quote_etree in response.xpath('//*[@itemscope]'):
            yield Quote(
                author=quote_etree.xpath('.//*[@itemprop="author"]/text()').get(),
                text=quote_etree.xpath('.//*[@itemprop="text"]/text()').get(),
                tags=quote_etree.xpath('.//*[@class="tag"]/text()').getall())

        # Recursively descend the next page.
        # Follow the "next page" link
        for next_url in response.xpath('//li[@class="next"]/a/@href').getall():
            yield scrapy.Request(
                response.urljoin(next_url),
                callback=self.parse)



@dataclasses.dataclass
class Quote:
    author: str
    text: str
    tags: list
