BOT_NAME = "scrapy_concurrency_test"
SPIDER_MODULES = ["scrapy_concurrency_test.spiders"]
NEWSPIDER_MODULE = "scrapy_concurrency_test.spiders"

ROBOTSTXT_OBEY = False

LOG_LEVEL = 'WARNING'

DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
}
