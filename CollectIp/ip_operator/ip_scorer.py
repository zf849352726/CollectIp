import requests
from concurrent.futures import ThreadPoolExecutor
import time
import logging

class IPScorer:
    def __init__(self):
        self.test_urls = [
            'http://httpbin.org/ip',  # 改用专门测试代理的网站
            'http://www.httpbin.org/get', 
        ]
        self.timeout = 10  # 增加超时时间

    def test_single_ip(self, ip):
        """测试单个IP的性能"""
        scores = []
        if ':' not in ip:
            logging.warning(f"IP格式不正确: {ip}")
            return 0
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        proxies = {
            'http': f'http://{ip}',
            'https': f'https://{ip}'
        }

        success_count = 0
        for url in self.test_urls:
            try:
                start_time = time.time()
                response = requests.get(url, proxies=proxies, timeout=self.timeout, headers=headers)
                elapsed_time = time.time() - start_time
                
                if response.status_code in [200, 301, 302]:
                    score = max(0, min(100, (self.timeout - elapsed_time) / self.timeout * 100))
                    scores.append(score)
                    success_count += 1
                    logging.info(f"IP: {ip} 访问 {url} 成功，得分: {score}")
            except Exception as e:
                logging.warning(f"IP: {ip} 访问 {url} 异常: {str(e)}")
                continue

        # 只要有超过一半的URL测试成功就计算平均分
        if success_count >= len(self.test_urls) // 2:
            return sum(scores) / len(scores)
        return 0

    def score_ip_pool(self, ip_list):
        """为IP池中的所有IP打分"""
        results = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ip = {executor.submit(self.test_single_ip, ip): ip for ip in ip_list}
            for future in future_to_ip:
                ip = future_to_ip[future]
                try:
                    score = future.result()
                    results[ip] = score
                except Exception as e:
                    print(f"IP {ip} 测试失败: {e}")
                    results[ip] = 0
        
        return results
