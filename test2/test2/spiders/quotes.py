import scrapy
import pathlib


class QuotesSpider(scrapy.Spider):
    name = 'quotes'
    allowed_domains = ['quotes.toscrape.com']
    start_urls = ['https://quotes.toscrape.com/page/1/']

    def parse(self, response):
        page = response.url.split('/')[-2]
        path = pathlib.Path(f'quotes-{page}.html')
        with path.open('w') as f:
            print(response.body, end='', file=f)
        self.log(f'Saved file {path}')
