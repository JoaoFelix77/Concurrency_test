BOT_NAME = "scrapy_playwright_test"

SPIDER_MODULES = ["scrapy_playwright_test.spiders"]
NEWSPIDER_MODULE = "scrapy_playwright_test.spiders"

ROBOTSTXT_OBEY = False


# 启用 Playwright 中间件
DOWNLOADER_MIDDLEWARES = {
    # "scrapy_playwright.middleware.ScrapyPlaywrightDownloadHandler": 543,
}

DOWNLOAD_HANDLERS = {
    # "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",        #HTTP模式不走playwright渲染
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}


# 设置 Twisted 的异步反应器
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# 最大并发数与超时设置
CONCURRENT_REQUESTS = 100  
DOWNLOAD_TIMEOUT = 10

RETRY_ENABLED = False

LOG_LEVEL = "INFO"  # 调试时改为 'DEBUG'


PLAYWRIGHT_MAX_CONTEXTS = 100

# Playwright 启动参数：使用 Playwright 默认内置的 Chromium
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": False,
    "timeout": 10000,
}

# 默认导航等待模式
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 10000
PLAYWRIGHT_DEFAULT_WAIT_UNTIL = "domcontentloaded"
PLAYWRIGHT_REUSE_CONTEXT = True


# 三种 Chrome 渲染上下文配置
PLAYWRIGHT_CONTEXTS = {
    # 默认 Chrome（启用 JS 和媒体）
    "chrome": {},

    # 禁用 JavaScript
    "chrome-no-js": {
        "java_script_enabled": False
    },

    # 禁用媒体（图片、插件）,具体在spiders中设置
    "chrome-no-media": {
        "bypass_csp": True,
    },
}
