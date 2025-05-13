import argparse
import csv
import statistics
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import psutil
from DrissionPage import ChromiumPage, ChromiumOptions

# 读取URL
def load_urls(file='url_list.txt', limit=10000):
    with open(file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    return urls[:limit]

# 设置资源快照
def get_resource_usage():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().used / 1024 / 1024  # MB
    io = psutil.disk_io_counters().read_bytes / 1024 / 1024  # MB
    return cpu, mem, io

# 页面抓取
def fetch(url, mode):
    try:
        if mode == 'miniblink':
            co = ChromiumOptions()
            co.set_browser_path('miniblink')  # 指定使用 miniblink
            page = ChromiumPage(co)

        elif mode == 'http':
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            session = requests.Session()

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/123.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }

            retries = Retry(
                total=2,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retries)
            session.mount("http://", adapter)
            session.mount("https://", adapter)

            try:
                start = time.time()
                resp = session.get(url, headers=headers, timeout=10)
                ok = resp.status_code == 200 and len(resp.text) > 0
                end = time.time()
                return end - start, ok
            except Exception:
                return 0, False

        else:
            co = ChromiumOptions()
            co.remote_port = 9222

            if mode == 'chrome-no-js':
                co.set_argument('--disable-javascript')
            elif mode == 'chrome-no-media':
                co.set_browser_path('chrome')
                co.set_argument('--blink-settings=imagesEnabled=false')
                co.set_argument('--disable-plugins')

            page = ChromiumPage(co)

        start = time.time()
        page.get(url, timeout=15)
        end = time.time()
        content = page.html
        ok = content is not None and len(content) > 0
        page.close()
        return end - start, ok

    except Exception as e:
        print(f"[Error] URL: {url} Error: {e}")
        return 0, False

# 并发测试
def run_test(mode, concurrency):
    urls = load_urls(limit=concurrency * 20)
    elapsed_list = []
    success_count = 0
    cpu_before, mem_before, io_before = get_resource_usage()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(fetch, url, mode) for url in urls]
        for future in tqdm(as_completed(futures), total=len(futures), desc=f'{mode}@{concurrency}'):
            elapsed, ok = future.result()
            if elapsed > 0:
                elapsed_list.append(elapsed)
            if ok:
                success_count += 1

    cpu_after, mem_after, io_after = get_resource_usage()

    avg = round(statistics.mean(elapsed_list), 3) if elapsed_list else 0
    p50 = round(statistics.median(elapsed_list), 3) if elapsed_list else 0
    p95 = round(statistics.quantiles(elapsed_list, n=100)[94], 3) if len(elapsed_list) >= 100 else 0

    cpu = round(cpu_after - cpu_before, 2)
    mem = round(mem_after - mem_before, 2)
    io = round(io_after - io_before, 2)
    success_rate = round(success_count / len(urls), 3)

    os.makedirs('results', exist_ok=True)
    log_file = 'results/logs.csv'
    write_header = not os.path.exists(log_file)

    with open(log_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(['Mode', 'Concurrency', 'Avg(s)', 'P50(s)', 'P95(s)', 'CPU(%)', 'Memory(MB)', 'IO(MB/s)', 'SuccessRate'])
        writer.writerow([f'DrissionPage-{mode}', concurrency, avg, p50, p95, cpu, mem, io, success_rate])

    print(f"[Done] {mode}@{concurrency}: Avg={avg}s, P50={p50}s, P95={p95}s, CPU={cpu}%, Mem={mem}MB, IO={io}MB/s, Success={success_rate}")

# 主函数入口
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DrissionPage并发性能测试')
    parser.add_argument('--mode', type=str, required=True,
                        choices=['chrome', 'chrome-no-js', 'chrome-no-media', 'miniblink', 'http'],
                        help='抓取模式')
    parser.add_argument('--concurrency', type=int, default=4, help='并发数量')

    args = parser.parse_args()
    run_test(args.mode, args.concurrency)

