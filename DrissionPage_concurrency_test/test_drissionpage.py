import argparse
import csv
import statistics
import time
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import psutil
from DrissionPage import ChromiumPage, ChromiumOptions
import math

# 读取URL
def load_urls(file='url_concurrency_list(Chrome).txt', limit=10000):        # 根据Chrome和HTTP模式切换URL列表
    with open(file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    return urls[:limit]

# 资源监控器
class ResourceMonitor:
    def __init__(self):
        self.cpu_samples = []
        self.mem_samples = []
        self.disk_io_start = psutil.disk_io_counters().read_bytes
        self.net_io_start  = psutil.net_io_counters().bytes_recv
        self._running = False

    def _sample(self):
        while self._running:
            self.cpu_samples.append(psutil.cpu_percent(interval=1))
            self.mem_samples.append(psutil.virtual_memory().used / 1024 / 1024)

    def start(self):
        self._running = True
        threading.Thread(target=self._sample, daemon=True).start()

    def stop(self, total_elapsed):
        self._running = False
        # 等待最后一个 interval 结束
        time.sleep(1)
        disk_end = psutil.disk_io_counters().read_bytes
        net_end  = psutil.net_io_counters().bytes_recv
        avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0
        avg_mem = sum(self.mem_samples) / len(self.mem_samples) if self.mem_samples else 0
        disk_mb = (disk_end - self.disk_io_start) / 1024 / 1024
        net_mb  = (net_end  - self.net_io_start)  / 1024 / 1024
        # 磁盘和网络 I/O速率 MB/s
        disk_speed = disk_mb / total_elapsed if total_elapsed else 0
        net_speed  = net_mb  / total_elapsed if total_elapsed else 0
        return round(avg_cpu,2), round(avg_mem,2), round(disk_speed,2), round(net_speed,2)

def fetch(url, mode):
    try:
        if mode == 'http':
            import requests
            from requests.adapters import HTTPAdapter, Retry
            sess = requests.Session()
            sess.mount('http://', HTTPAdapter(max_retries=Retry(total=0)))
            sess.mount('https://', HTTPAdapter(max_retries=Retry(total=0)))
            start = time.time()
            r = sess.get(url, timeout=10)
            ok = (r.status_code==200 and len(r.text)>0)
            return time.time()-start, ok
        else:
            co = ChromiumOptions()
            co.remote_port = 9222
            if mode=='chrome-no-js':
                co.set_argument('--disable-javascript')
            elif mode=='chrome-no-media':
                co.set_browser_path('chrome')
                co.set_argument('--blink-settings=imagesEnabled=false')
                co.set_argument('--disable-plugins')
            page = ChromiumPage(co)
            start = time.time()
            page.get(url, timeout=10)
            ok = bool(page.html)
            page.close()
            return time.time()-start, ok
    except:
        return 0, False

def run_test(mode, concurrency):
    urls = load_urls(limit=10000)
    times = []
    succ = 0

    mon = ResourceMonitor()
    start_wall = time.time()
    mon.start()

    with ThreadPoolExecutor(concurrency) as ex:
        for elapsed, ok in tqdm(ex.map(lambda u: fetch(u,mode), urls), total=len(urls), desc=f'{mode}@{concurrency}'):
            if elapsed>0: times.append(elapsed)
            if ok: succ+=1

    wall_time = time.time() - start_wall
    cpu, mem, disk_speed, net_speed = mon.stop(wall_time)

    # 时间指标
    n = len(times)
    avg = round(statistics.mean(times),3) if n else 0
    p50 = round(statistics.median(times),3)    if n else 0
    if n:
        times_sorted = sorted(times)
        idx = max(0, min(n-1, math.ceil(0.95*n)-1))
        p95 = round(times_sorted[idx],3)
    else:
        p95 = 0

    sr = round(succ/len(urls),3)
    throughput = round(len(times) / wall_time, 2) if wall_time > 0 else 0

    os.makedirs('results', exist_ok=True)
    lp = 'results/log.csv'
    write_hdr = not os.path.exists(lp)
    with open(lp,'a',newline='',encoding='utf-8') as f:
        w = csv.writer(f)
        if write_hdr:
            w.writerow(['Mode','Concurrency','Avg(s)','P50(s)','P95(s)','CPU(%)','Memory(MB)','Net I/O(MB/s)','Throughput(req/s)','SuccessRate'])
        w.writerow([f'DrissionPage-{mode}',concurrency,avg,p50,p95,cpu,mem,net_speed,throughput,sr])

    print(f"[Done] {mode}@{concurrency}: Avg={avg}s, P50={p50}s, P95={p95}s, "
          f"CPU={cpu}%, Mem={mem}MB, Net I/O={net_speed}MB/s, "
          f"Throughput={throughput}req/s, SR={sr}")

if __name__=='__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['http','chrome','chrome-no-js','chrome-no-media'], required=True)
    p.add_argument('--concurrency', type=int, default=4)
    args = p.parse_args()
    run_test(args.mode, args.concurrency)

