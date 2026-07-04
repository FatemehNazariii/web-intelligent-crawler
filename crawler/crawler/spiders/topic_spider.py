import scrapy

class TopicSpider(scrapy.Spider):
    name = "topic"

    def __init__(self, urls=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = urls.split(",") if urls else []

    def parse(self, response):
        yield {
            "url": response.url,
            "html": response.text
        }