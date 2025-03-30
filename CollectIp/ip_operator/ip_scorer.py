import requests
from concurrent.futures import ThreadPoolExecutor
import time
import logging
from django.apps import apps

class IPScorer:
    def __init__(self):
        self.http_test_urls = [
            'http://httpbin.org/ip',
            'http://www.httpbin.org/get',
        ]
        self.https_test_urls = [
            'https://httpbin.org/ip',
            'https://www.httpbin.org/get',
        ]
        self.timeout = 10  # 超时时间

    def test_single_ip(self, ip, ssl_support=None):
        """测试单个IP的性能
        
        Args:
            ip (str): IP地址和端口，格式为 ip:port
            ssl_support (str, optional): 数据库中的SSL支持状态，如果为None则会测试所有URL
        """
        scores = []
        if ':' not in ip:
            logging.warning(f"IP格式不正确: {ip}")
            return 0
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 根据SSL支持情况选择要测试的URL
        test_urls = self.http_test_urls.copy()
        if ssl_support is None or 'not' not in str(ssl_support).lower():
            test_urls.extend(self.https_test_urls)
            # 支持HTTPS
            proxies = {
                'http': f'http://{ip}',
                'https': f'https://{ip}'
            }
        else:
            # 不支持HTTPS，只使用HTTP代理
            proxies = {
                'http': f'http://{ip}',
                'https': f'http://{ip}'  # 使用HTTP代理尝试处理HTTPS请求
            }
            
        logging.info(f"测试IP: {ip}, SSL支持: {ssl_support}, 测试URL数量: {len(test_urls)}")

        success_count = 0
        for url in test_urls:
            try:
                start_time = time.time()
                response = requests.get(url, proxies=proxies, timeout=self.timeout, headers=headers)
                elapsed_time = time.time() - start_time
                
                if response.status_code in [200, 301, 302]:
                    score = max(0, min(100, (self.timeout - elapsed_time) / self.timeout * 100))
                    scores.append(score)
                    success_count += 1
                    logging.info(f"IP: {ip} 访问 {url} 成功，得分: {score:.2f}，耗时: {elapsed_time:.2f}秒")
            except Exception as e:
                logging.warning(f"IP: {ip} 访问 {url} 异常: {str(e)}")
                continue

        # 只要有超过一半的URL测试成功就计算平均分
        min_success = 1  # 至少成功1个URL
        if success_count >= min_success:
            return sum(scores) / len(scores)
        return 0

    def score_ip_pool(self, ip_list):
        """为IP池中的所有IP打分"""
        try:
            # 动态获取IpData模型
            IpData = apps.get_model('index', 'IpData')
            
            # 获取所有IP的SSL支持信息
            ip_ssl_info = {}
            for ip_obj in IpData.objects.filter(server__in=ip_list):
                ip_ssl_info[ip_obj.server] = ip_obj.ssl
                
            results = {}
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_ip = {
                    executor.submit(
                        self.test_single_ip, 
                        ip, 
                        ip_ssl_info.get(ip)
                    ): ip for ip in ip_list
                }
                
                for future in future_to_ip:
                    ip = future_to_ip[future]
                    try:
                        score = future.result()
                        results[ip] = score
                        logging.info(f"IP {ip} 最终得分: {score:.2f}")
                    except Exception as e:
                        logging.error(f"IP {ip} 测试失败: {e}")
                        results[ip] = 0
            
            return results
        except Exception as e:
            logging.error(f"获取IP SSL信息时出错: {e}")
            # 回退到不考虑SSL支持的测试
            results = {}
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_ip = {executor.submit(self.test_single_ip, ip): ip for ip in ip_list}
                for future in future_to_ip:
                    ip = future_to_ip[future]
                    try:
                        score = future.result()
                        results[ip] = score
                    except Exception as e:
                        logging.error(f"IP {ip} 测试失败: {e}")
                        results[ip] = 0
            
            return results
