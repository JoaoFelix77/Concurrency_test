class PlaywrightMediaBlockMiddleware:
    def process_request(self, request, spider):
        if request.meta.get("playwright") and spider.mode == "chrome-no-media":
            request.meta["playwright_page_methods"] = [
                ("route", "**/*.{png,jpg,jpeg,gif,webp,svg,mp4,avi,mov}", 
                 lambda route: route.abort()),
                *request.meta.get("playwright_page_methods", [])
            ]
