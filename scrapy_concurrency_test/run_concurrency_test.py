import os 
os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "scrapy_playwright_test.settings")

from scrapy.settings import Settings
import scrapy_playwright_test.settings as my_settings
import argparse
import time
import statistics
import psutil
import threading
import csv
from tqdm import tqdm

from scrapy.crawler import CrawlerProcess
from scrapy_playwright_test.spiders.test_spider import TestSpider


def load_urls(path="url_concurrency_list(Chrome).txt"):         # 根据HTTP和Chrome模式切换
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def update_stats(stats, total, pbar): 
    now = time.time()
    done = stats["success"] + stats["failed"]
    pbar.n = done; pbar.refresh()

    # 1. 时延统计
    d = stats["durations"]
    avg = statistics.mean(d) if d else 0
    p50 = statistics.median(d) if d else 0
    p95 = statistics.quantiles(d, n=100)[94] if len(d) >= 100 else 0

    # 2. 资源统计
    cpu = psutil.cpu_percent()
    mem_mb = psutil.virtual_memory().used / 1024 / 1024

    # 3. 网络和磁盘快照
    disk_curr = psutil.disk_io_counters().read_bytes
    net_io = psutil.net_io_counters()
    net_curr = net_io.bytes_sent + net_io.bytes_recv

    # 4. 增量与速率
    dt = now - stats["last_time"]
    delta_disk = disk_curr - stats["last_disk"]
    delta_net = net_curr - stats["last_net"]
    # 如果后续需要磁盘速率可加上
    #disk_rate = (delta_disk / 1024 / 1024) / dt if dt > 0 else 0
    net_rate = (delta_net / 1024 / 1024) / dt if dt > 0 else 0

    # 5. 吞吐量
    elapsed = now - stats["start_time"]
    throughput = done / elapsed if elapsed > 0 else 0

    # 6. 成功率
    sr = stats["success"] / done if done > 0 else 0

    tqdm.write(
        f"[Progress] S={stats['success']} F={stats['failed']} | "
        f"avg={avg:.2f}s p50={p50:.2f}s p95={p95:.2f}s | "
        f"CPU={cpu:.1f}% Memory={mem_mb:.1f}MB | "
        f"Net I/O={net_rate:.2f}MB/s | "
        f"Throughput={throughput:.2f}req/s | "
        f"SuccessRate={sr:.3f}"
    )

    # 更新快照
    stats["last_time"] = now
    stats["last_disk"] = disk_curr
    stats["last_net"] = net_curr

    if done < total:
        threading.Timer(5, update_stats, args=[stats, total, pbar]).start()

def run_spider(mode, urls, concurrency):
    stats = {
        "durations": [], "success": 0, "failed": 0,
        "start_time": time.time(),
        "start_disk": psutil.disk_io_counters().read_bytes,
        "start_net": (lambda io: io.bytes_sent + io.bytes_recv)(psutil.net_io_counters()),
    }
    stats["last_time"] = stats["start_time"]
    stats["last_disk"] = stats["start_disk"]
    stats["last_net"] = stats["start_net"]

    total = len(urls)
    pbar = tqdm(total=total, desc="Crawling Progress")
    update_stats(stats, total, pbar)

    settings = Settings()
    settings.setmodule(my_settings)
    settings.set("CONCURRENT_REQUESTS", concurrency)
    settings.set("PLAYWRIGHT_MAX_CONTEXTS", concurrency)

    process = CrawlerProcess(settings=settings)
    process.crawl(TestSpider, urls=urls, mode=mode, stats=stats)
    process.start()
    pbar.close()
    return stats


def save_stats(stats, mode, concurrency):
    d = stats["durations"]
    avg = statistics.mean(d) if d else 0
    p50 = statistics.median(d) if d else 0
    p95 = statistics.quantiles(d, n=100)[94] if len(d) >= 100 else 0
    cpu = psutil.cpu_percent()
    mem_mb = psutil.virtual_memory().used / 1024 / 1024

    # 用总时间计算平均吞吐
    end_time = time.time()
    duration = end_time - stats["start_time"]
    done = stats["success"] + stats["failed"]
    avg_throughput = done / duration if duration > 0 else 0

    # 计算平均网络 I/O MB/s
    end_net = (lambda io: io.bytes_sent + io.bytes_recv)(psutil.net_io_counters())
    total_net = end_net - stats["start_net"]
    avg_net_rate = (total_net / 1024 / 1024) / duration if duration > 0 else 0
    
    sr = stats["success"] / done if done > 0 else 0

    os.makedirs("results", exist_ok=True)
    path = "results/performance_log.csv"
    write_header = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow([
                "Mode","Concurrency","Avg(s)","P50(s)","P95(s)",
                "CPU(%)","Memory(MB)","Net I/O(MB/s)","Throughput(req/s)","SuccessRate"
            ])
        w.writerow([
            mode, concurrency,
            f"{avg:.3f}", f"{p50:.3f}", f"{p95:.3f}",
            f"{cpu:.1f}", f"{mem_mb:.1f}",
            f"{avg_net_rate:.2f}",  
            f"{avg_throughput:.2f}",
            f"{sr:.3f}"
        ])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True,
                        choices=["http", "chrome", "chrome-no-js", "chrome-no-media"],
                        help="抓取模式：http 或 Playwright 渲染")
    parser.add_argument("--concurrency", type=int, default=16,
                        help="Scrapy 并发请求数及 Playwright 上下文数")
    args = parser.parse_args()

    urls = load_urls("url_concurrency_list(Chrome).txt")           # 根据HTTP和Chrome模式切换
    print(f"Loaded {len(urls)} URLs → mode={args.mode}, concurrency={args.concurrency}")

    start = time.time()
    stats = run_spider(args.mode, urls, args.concurrency)
    duration = time.time() - start

    save_stats(stats, f"Scrapy-{args.mode}", args.concurrency)
    print(f"Done in {duration:.1f}s; results saved to results/performance_log.csv")

