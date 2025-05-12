import argparse
import os
import csv
import statistics
import psutil
import time
import threading
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor
from scrapy_concurrency_test.spiders.test_spider import TestSpider


#资源监控
class ResourceMonitor(threading.Thread):
    def __init__(self, pid):
        super().__init__()
        self.pid = pid
        self.cpu = 0
        self.mem = 0
        self.io = 0
        self.running = True
        self.daemon = True
        self.io_start = None
        
    def run(self):
        proc = psutil.Process(self.pid)
        self.io_start = proc.io_counters()
        cpu_samples = []
        mem_samples = []
        io_read_samples = []
        io_write_samples = []
        
        while self.running:
            try:
                # CPU和内存
                cpu_samples.append(proc.cpu_percent(interval=0.5))
                mem_samples.append(proc.memory_info().rss / 1024 / 1024)  # MB
                
                # IO
                io_counters = proc.io_counters()
                io_read_samples.append(io_counters.read_bytes / 1024 / 1024)  # MB
                io_write_samples.append(io_counters.write_bytes / 1024 / 1024)  # MB
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
        
        # 计算最终指标
        self.cpu = statistics.mean(cpu_samples) if cpu_samples else 0
        self.mem = statistics.mean(mem_samples) if mem_samples else 0
        self.io = statistics.mean([r+w for r,w in zip(io_read_samples, io_write_samples)]) if io_read_samples else 0


#生成Scrapy配置
def get_custom_settings(mode, concurrency):   
    settings = get_project_settings()
    settings.update({
        'CONCURRENT_REQUESTS': concurrency,
        'DOWNLOAD_TIMEOUT': 30,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 403, 429],
        'LOG_LEVEL': 'INFO',
        'DUPEFILTER_DEBUG': True,
        'HTTPCACHE_ENABLED': False
    })

    if mode.startswith('chrome'):
        settings.update({
            'DOWNLOADER_MIDDLEWARES': {
                'scrapy_selenium.SeleniumMiddleware': 800,
                'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 100,
            },
            'SELENIUM_DRIVER_NAME': 'chrome',
            'SELENIUM_DRIVER_ARGUMENTS': [
                '--headless',
                '--no-sandbox',
                '--disable-gpu',
                '--disable-dev-shm-usage',
                *(['--disable-javascript'] if 'no-js' in mode else []),
                *(['--blink-settings=imagesEnabled=false'] if 'no-media' in mode else [])
            ]
        })
    return settings

#计算时间指标
def calculate_metrics(durations):
    if not durations:
        return 0, 0, 0
    
    try:
        avg = round(statistics.mean(durations), 3)
        p50 = round(statistics.median(durations), 3)
        p95 = round(statistics.quantiles(durations, n=20)[-1], 3) if len(durations) >=5 else 0
        return avg, p50, p95
    except:
        return 0, 0, 0

#主测试函数
def run_test(mode, concurrency):
    try:
        with open('url_list.txt', 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
            
        if not urls:
            print("Error: URL文件为空，请检查url_list.txt内容")
            return
        
        print(f"成功从url_list.txt加载 {len(urls)} 个URL")
        
    except FileNotFoundError:
        print("Error: 未找到url_list.txt文件，请创建文件并每行一个URL")
        return
    except Exception as e:
        print(f"读取URL文件出错: {str(e)}")
        return

    stats = {
        'durations': [],
        'success': 0,
        'failed': 0,
        'start_time': time.time()
    }

    settings = get_custom_settings(mode, concurrency)
    runner = CrawlerRunner(settings)
    
    # 启动资源监控
    monitor = ResourceMonitor(os.getpid())
    monitor.start()

    # 运行爬虫
    deferred = runner.crawl(TestSpider, urls=urls, stats=stats)
    deferred.addBoth(lambda _: reactor.stop())
    reactor.run()
    
    # 停止监控
    monitor.running = False
    monitor.join()

    # 计算所有指标
    total_time = time.time() - stats['start_time']
    avg, p50, p95 = calculate_metrics(stats['durations'])
    success_rate = stats['success'] / len(urls) if urls else 0
    
    # 打印结果
    print(f"\n[Final Results] {mode}@{concurrency}")
    print(f"Timing (s): Avg={avg}, P50={p50}, P95={p95}")
    print(f"Success: {stats['success']}/{len(urls)} ({success_rate:.1%})")
    print(f"Resources: CPU={monitor.cpu:.1f}%, Mem={monitor.mem:.1f}MB, IO={monitor.io:.2f}MB/s")

    # 保存完整指标到CSV
    save_to_csv(mode, concurrency, avg, p50, p95, monitor.cpu, monitor.mem, monitor.io, success_rate)

def save_to_csv(mode, concurrency, avg, p50, p95, cpu, mem, io, success_rate):
    os.makedirs('results', exist_ok=True)
    file_path = 'results/performance_logs.csv'
    file_exists = os.path.isfile(file_path)
    
    with open(file_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # 写入表头（如果文件不存在）
        if not file_exists:
            writer.writerow([
                'Mode',
                'Concurrency',
                'Avg(s)',
                'P50(s)',
                'P95(s)',
                'CPU(%)',
                'Memory(MB)',
                'IO(MB/s)',
                'SuccessRate'
            ])
        
        # 写入数据行
        writer.writerow([
            f'Scrapy-{mode}',
            concurrency,
            avg,
            p50,
            p95,
            round(cpu, 2),
            round(mem, 2),
            round(io, 2),
            round(success_rate, 4)
        ])
    
    print(f"Results saved to {file_path} with 9 metrics")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrapy并发性能测试')
    parser.add_argument('--mode', required=True,
                       choices=['chrome', 'chrome-no-js', 'chrome-no-media', 'http'],
                       help='Test mode: chrome|chrome-no-js|chrome-no-media|http')
    parser.add_argument('--concurrency', type=int, default=1,
                       help='Number of concurrent requests (default: 1)')
    args = parser.parse_args()
    
    print(f"Starting performance test in {args.mode} mode (concurrency={args.concurrency})...")
    run_test(args.mode, args.concurrency)
