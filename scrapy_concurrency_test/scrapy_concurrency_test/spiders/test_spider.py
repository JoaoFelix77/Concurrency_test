import scrapy
import time
from scrapy_playwright.page import PageMethod


class TestSpider(scrapy.Spider):
    name = "test_spider"

    def __init__(self, urls=None, mode="http", stats=None, **kwargs):
        super().__init__(**kwargs)
        self.urls = urls.split(",") if isinstance(urls, str) else (urls or [])
        self.mode = mode
        self.stats = stats or {"durations": [], "success": 0, "failed": 0}
        self.logger.info(f"[Spider init] URLs={len(self.urls)}, mode={self.mode}")

    def start_requests(self):
        self.logger.info(f"[Spider] start_requests  mode={self.mode}, urls={len(self.urls)}")
        for url in self.urls:
            meta = {"start_time": time.time()}

            if self.mode == "http":
                # 普通 HTTP 请求
                yield scrapy.Request(
                    url,
                    callback=self.parse,
                    errback=self.errback,
                    meta=meta,
                    dont_filter=True,
                )

            else:
                # Playwright 渲染请求
                meta.update({
                    "playwright": True,
                    "playwright_context": self.mode,
                    "playwright_include_page": False,
                })

                # 如果是 chrome-no-media 模式，加路由拦截图片/媒体
                if self.mode == "chrome-no-media":
                    meta["playwright_page_methods"] = [
                        PageMethod(
                            "route",
                            "**/*",
                            # 拦截图片、媒体、字体等
                            lambda route, request: (
                                route.abort()
                                if request.resource_type in ("image", "media", "font")
                                else route.continue_()
                            ),
                        )
                    ]

                self.logger.info(f"Request (playwright) - {url}")
                yield scrapy.Request(
                    url,
                    callback=self.parse,
                    errback=self.errback,
                    meta=meta,
                    dont_filter=True,
                )

    async def parse(self, response):
        # 打印 meta_keys，确认 Playwright 渲染生效
        self.logger.info(f"[parse] meta_keys={list(response.meta.keys())}")

        
        dur = time.time() - response.meta.get("start_time", time.time())
        self.stats["durations"].append(dur)
        if response.status == 200 and len(response.text) > 100:
            self.stats["success"] += 1
        else:
            self.stats["failed"] += 1

        self.logger.debug(f"[parse] {response.url} | {dur:.2f}s | {response.status}")

    def errback(self, failure):
        dur = time.time() - failure.request.meta.get("start_time", time.time())
        self.stats["failed"] += 1
        self.logger.warning(f"[errback] {failure.request.url} failed after {dur:.2f}s")
