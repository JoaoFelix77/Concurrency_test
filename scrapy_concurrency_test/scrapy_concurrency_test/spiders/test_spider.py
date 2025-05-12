import scrapy
import time

class TestSpider(scrapy.Spider):
    name = "test_spider"
    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'AUTOTHROTTLE_ENABLED': False
    }

    def __init__(self, urls=None, stats=None, **kwargs):
        super().__init__(**kwargs)
        self.start_urls = urls or []
        self.stats = stats or {
            'durations': [],
            'success': 0,
            'failed': 0
        }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={'start_time': time.time()},
                callback=self.parse_response,
                errback=self.parse_error,
                dont_filter=True
            )

    def parse_response(self, response):
        duration = time.time() - response.meta['start_time']
        self.stats['durations'].append(duration)
        
        if response.status == 200 and len(response.text) > 100:
            self.stats['success'] += 1
            self.logger.info(f"Success: {response.url} ({duration:.2f}s)")
        else:
            self.stats['failed'] += 1
            self.logger.warning(f"Soft Fail: {response.url} (Status: {response.status})")

    def parse_error(self, failure):
        self.stats['failed'] += 1
        self.logger.error(f"Hard Fail: {failure.request.url} - {failure.getErrorMessage()}")
