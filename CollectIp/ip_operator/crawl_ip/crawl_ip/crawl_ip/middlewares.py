# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter

import random
import pymysql
from scrapy.exceptions import NotConfigured
import time
import sys
import os
from pathlib import Path

# 添加ip_operator到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from ip_operator.ip_scorer import IPScorer  # 导入IPScorer类


class CrawlIpSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn't have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class CrawlIpDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class ProxyMiddleware:
    def __init__(self, db_host, db_user, db_password, db_name):
        """初始化数据库连接参数"""
        self.db_host = db_host
        self.db_user = db_user
        self.db_password = db_password
        self.db_name = db_name
        self.proxy_list = []
        self.current_proxy = None
        self.blacklist = set()  # 用于记录失败的代理
        self.update_interval = 300  # 5分钟更新一次代理列表
        self.last_update_time = 0
        # 创建IPScorer实例
        self.scorer = IPScorer()
        self.debug = True  # 始终启用调试模式
        self.proxy_usage_stats = {}  # 跟踪代理使用情况
        self.proxy_success_stats = {}  # 跟踪代理成功情况
        
        print("【代理中间件】初始化完成，调试模式已启用")
        
    @classmethod
    def from_crawler(cls, crawler):
        """从settings获取数据库配置"""
        if not crawler.settings.getbool('PROXY_ENABLED'):
            raise NotConfigured
            
        middleware = cls(
            db_host=crawler.settings.get('MYSQL_HOST'),
            db_user=crawler.settings.get('MYSQL_USER'),
            db_password=crawler.settings.get('MYSQL_PASSWORD'),
            db_name=crawler.settings.get('MYSQL_DATABASE')
        )
        
        # 设置调试标志，但不影响始终启用的调试输出
        debug_enabled = crawler.settings.getbool('PROXY_DEBUG', True)
        print(f"【代理中间件】PROXY_DEBUG设置为: {debug_enabled}")
        return middleware
        
    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.db_host,
            user=self.db_user,
            password=self.db_password,
            database=self.db_name,
            charset='utf8mb4'
        )
        
    def update_proxy_list(self):
        """从数据库更新代理IP列表"""
        current_time = time.time()
        # 检查是否需要更新代理列表
        if current_time - self.last_update_time < self.update_interval and self.proxy_list:
            return

        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT server 
                    FROM index_ipdata 
                    WHERE score >= 80  -- 只选择评分大于等于80的代理
                    AND server NOT IN (
                        SELECT server 
                        FROM index_ipdata 
                        WHERE updated_at < DATE_SUB(NOW(), INTERVAL 1 HOUR)
                    )  -- 排除1小时内未更新的代理
                    AND country IN ('China', 'Japan', 'Korea')  -- 优先选择亚洲代理
                    ORDER BY 
                        score DESC,  -- 按分数降序
                        ping ASC,    -- 按延迟升序
                        speed ASC    -- 按速度升序
                    LIMIT 50        -- 限制代理数量
                """
                cursor.execute(sql)
                results = cursor.fetchall()
                
                # 更新代理列表，排除黑名单中的代理
                self.proxy_list = [
                    row[0] for row in results 
                    if row[0] not in self.blacklist
                ]
                
                self.last_update_time = current_time
                
                # 如果代理列表为空，使用备用查询
                if not self.proxy_list:
                    backup_sql = """
                        SELECT server 
                        FROM index_ipdata 
                        WHERE score >= 50 
                        AND server NOT IN (
                            SELECT server FROM index_ipdata 
                            WHERE updated_at < DATE_SUB(NOW(), INTERVAL 2 HOUR)
                        )
                        ORDER BY score DESC 
                        LIMIT 20
                    """
                    cursor.execute(backup_sql)
                    backup_results = cursor.fetchall()
                    self.proxy_list = [
                        row[0] for row in backup_results 
                        if row[0] not in self.blacklist
                    ]
                
        except Exception as e:
            print(f"更新代理列表出错: {e}")
        finally:
            if conn:
                conn.close()

    def update_proxy_score(self, proxy, success=True):
        """更新代理评分"""
        try:
            if success:
                # 使用IPScorer进行评分
                score = self.scorer.test_single_ip(proxy)
            else:
                score = 0

            conn = self.get_connection()
            with conn.cursor() as cursor:
                sql = """
                UPDATE index_ipdata 
                SET score = %s,
                            updated_at = NOW()
                        WHERE server = %s
                    """
                cursor.execute(sql, (score, proxy))
                conn.commit()
        except Exception as e:
            print(f"更新代理分数出错: {e}")
        finally:
            if conn:
                conn.close()

    def get_random_proxy(self):
        """获取随机代理"""
        if not self.proxy_list:
            if self.debug:
                print("【代理中间件】正在更新代理列表...")
            self.update_proxy_list()
            if self.debug and self.proxy_list:
                print(f"【代理中间件】成功获取 {len(self.proxy_list)} 个代理")
            
        if self.proxy_list:
            proxy = random.choice(self.proxy_list)
            # 更新代理使用统计
            self.proxy_usage_stats[proxy] = self.proxy_usage_stats.get(proxy, 0) + 1
            return proxy
        return None
        
    def process_request(self, request, spider):
        """处理请求，添加代理"""
        proxy = self.get_random_proxy()
        if proxy:
            # 根据请求的URL协议选择代理协议
            if request.url.startswith('https://'):
                request.meta['proxy'] = f"https://{proxy}"
            else:
                request.meta['proxy'] = f"http://{proxy}"
                
            # 始终输出代理调试信息
            protocol = "HTTPS" if request.url.startswith('https://') else "HTTP"
            print(f"【代理中间件】为请求 {request.url[:50]}... 分配{protocol}代理: {proxy} (已使用{self.proxy_usage_stats.get(proxy, 0)}次)")
            # 每50个请求输出一次代理使用统计信息
            if sum(self.proxy_usage_stats.values()) % 50 == 0:
                self._print_proxy_stats()
            
            spider.logger.debug(f'使用代理: {proxy}')
            
    def process_response(self, request, response, spider):
        """处理响应"""
        proxy = request.meta.get('proxy', '').replace('http://', '').replace('https://', '')
        
        if response.status != 200:
            if proxy:
                self.update_proxy_score(proxy, success=False)
                self.blacklist.add(proxy)
                if self.debug:
                    print(f"【代理中间件】代理失败: {proxy}, 状态码: {response.status}, URL: {request.url[:50]}...")
                spider.logger.warning(f'代理失败: {proxy}')
            
            # 重试请求
            request.dont_filter = True
            new_proxy = self.get_random_proxy()
            if new_proxy:
                # 根据请求的URL协议选择代理协议
                if request.url.startswith('https://'):
                    request.meta['proxy'] = f"https://{new_proxy}"
                else:
                    request.meta['proxy'] = f"http://{new_proxy}"
                    
                if self.debug:
                    print(f"【代理中间件】使用新代理重试: {new_proxy}")
            return request
        else:
            # 请求成功，更新代理评分
            if proxy:
                self.update_proxy_score(proxy, success=True)
                # 更新代理成功统计
                self.proxy_success_stats[proxy] = self.proxy_success_stats.get(proxy, 0) + 1
                if self.debug:
                    success_rate = self.proxy_success_stats.get(proxy, 0) / self.proxy_usage_stats.get(proxy, 1)
                    print(f"【代理中间件】代理成功: {proxy}, 成功率: {success_rate:.2%}")
        
        return response
        
    def process_exception(self, request, exception, spider):
        """处理异常"""
        proxy = request.meta.get('proxy', '').replace('http://', '').replace('https://', '')
        if proxy:
            self.update_proxy_score(proxy, success=False)
            self.blacklist.add(proxy)
            if self.debug:
                print(f"【代理中间件】代理异常: {proxy}, 异常: {type(exception).__name__}, URL: {request.url[:50]}...")
            spider.logger.warning(f'代理异常: {proxy}, 异常: {exception}')
        
        # 重试请求
        request.dont_filter = True
        new_proxy = self.get_random_proxy()
        if new_proxy:
            # 根据请求的URL协议选择代理协议
            if request.url.startswith('https://'):
                request.meta['proxy'] = f"https://{new_proxy}"
            else:
                request.meta['proxy'] = f"http://{new_proxy}"
                
            if self.debug:
                print(f"【代理中间件】使用新代理重试: {new_proxy}")
        return request
        
    def _print_proxy_stats(self):
        """打印代理使用统计信息"""
        if not self.debug:
            return
            
        # 计算成功率
        print("\n==== 代理使用统计 ====")
        
        # 根据使用次数排序
        sorted_proxies = sorted(self.proxy_usage_stats.items(), key=lambda x: x[1], reverse=True)
        
        for proxy, count in sorted_proxies[:10]:  # 只显示前10个
            success_count = self.proxy_success_stats.get(proxy, 0)
            success_rate = success_count / count if count > 0 else 0
            print(f"代理: {proxy} - 使用: {count}次, 成功: {success_count}次, 成功率: {success_rate:.2%}")
            
        total_usage = sum(self.proxy_usage_stats.values())
        total_success = sum(self.proxy_success_stats.values())
        overall_success_rate = total_success / total_usage if total_usage > 0 else 0
        print(f"总体统计: 使用 {total_usage}次, 成功 {total_success}次, 成功率: {overall_success_rate:.2%}")
        print("=====================\n")


class RandomUserAgentMiddleware:
    """高级请求头定制中间件
    
    提供智能化的请求头管理，包括：
    1. 更现代的User-Agent池
    2. 根据不同网站定制请求头
    3. 模拟真实浏览器指纹
    4. 智能Cookie处理
    5. 防止浏览器指纹识别
    """
    
    def __init__(self):
        # 更新更现代的User-Agent列表
        self.user_agents = [
            # Windows + Chrome (最新版本)
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            # Windows + Edge (最新版本)
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
            # Windows + Firefox (最新版本)
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
            # MacOS + Chrome
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            # MacOS + Safari
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            # iOS + Safari (最新版本)
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            # Android + Chrome
            'Mozilla/5.0 (Linux; Android 14; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36',
        ]
        
        # Accept-Language列表
        self.accept_language = [
            'zh-CN,zh;q=0.9,en;q=0.8',
            'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'en-US,en;q=0.9,zh-CN;q=0.8',
            'en-GB,en;q=0.9,en-US;q=0.8',
            'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
        ]
        
        # Accept头部
        self.accept = [
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        ]
        
        # 网站特定的请求头模板
        self.site_specific_templates = {
            'douban.com': {
                # 保持不变的浏览器参数
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "zh-CN,zh;q=0.9",
            },
            'zhihu.com': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'sec-ch-ua': '"Google Chrome";v="121", "Chromium";v="121", "Not A(Brand";v="99"',
            },
            'weibo.com': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://weibo.com/',
            }
            # 可以添加更多网站特定的请求头
        }
        
        # Chrome版本号列表
        self.chrome_versions = ['110', '111', '112', '113', '114', '115', '116', '117', '118', '119', '120', '121', '122']
        
        # 浏览器平台列表
        self.platforms = ['"Windows"', '"macOS"', '"Linux"', '"Android"', '"iOS"']
        
        # 移动设备指示
        self.mobile_indicators = ['?0', '?1']
        
        # 常用的Cookie值，用于模拟已有的会话状态
        self.cookie_templates = [
            '_ga=GA1.2.{random_id}.{timestamp}; _gid=GA1.2.{random_id2}.{timestamp}',
            'bid={random_char}; ll="{random_num}"; _ga=GA1.2.{random_id}.{timestamp}',
            '_octo=GH1.1.{random_id}.{timestamp}; tz=Asia%2FShanghai',
        ]
        
        # 参考屏幕分辨率
        self.screen_resolutions = [
            '1920x1080', '2560x1440', '1366x768', '1440x900', 
            '1536x864', '2560x1600', '3840x2160', '1280x720'
        ]

        # 添加调试支持
        self.debug = True  # 调试模式始终开启
        self.ua_usage_stats = {}  # 用户代理使用统计
        self.domain_stats = {}  # 域名访问统计
        
        print("【UA中间件】初始化完成，调试模式已启用")

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        # 设置调试标志但不影响输出
        debug_enabled = crawler.settings.getbool('UA_DEBUG', True)
        print(f"【UA中间件】UA_DEBUG设置为: {debug_enabled}")
        return middleware
    
    def _get_site_domain(self, url):
        """从URL提取网站域名"""
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # 提取主域名(例如从www.example.com得到example.com)
        domain_parts = domain.split('.')
        if len(domain_parts) > 2 and domain_parts[0] != 'www':
            return domain
        elif len(domain_parts) > 2 and domain_parts[0] == 'www':
            return '.'.join(domain_parts[1:])
        return domain
    
    def _get_random_cookie(self):
        """生成随机Cookie值"""
        import time
        import random
        import string
        
        timestamp = int(time.time())
        random_id = random.randint(1000000000, 9999999999)
        random_id2 = random.randint(1000000000, 9999999999)
        random_char = ''.join(random.choices(string.ascii_lowercase + string.digits, k=11))
        random_num = random.randint(1, 7)
        
        template = random.choice(self.cookie_templates)
        return template.format(
            random_id=random_id,
            random_id2=random_id2,
            timestamp=timestamp,
            random_char=random_char,
            random_num=random_num
        )
    
    def _get_browser_fingerprint_headers(self):
        """生成模拟浏览器指纹的请求头"""
        import random
        
        chrome_version = random.choice(self.chrome_versions)
        platform = random.choice(self.platforms)
        mobile = random.choice(self.mobile_indicators)
        
        return {
            'sec-ch-ua': f'"Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}", "Not A(Brand";v="99"',
            'sec-ch-ua-platform': platform,
            'sec-ch-ua-mobile': mobile,
        }
    
    def _get_referrer(self, url):
        """智能生成合理的Referer值"""
        from urllib.parse import urlparse
        import random
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        scheme = parsed_url.scheme
        
        # 对于不同类型的页面生成不同的referer
        if '/search' in url:
            return f"{scheme}://{domain}/"
        elif any(path_part in url for path_part in ['/detail', '/item', '/product', '/subject']):
            # 详情页，可能是从搜索页来的
            return f"{scheme}://{domain}/search"
        elif '/user' in url or '/member' in url or '/profile' in url:
            # 用户页面，可能是从首页来的
            return f"{scheme}://{domain}/"
        
        # 随机决定是否添加referer
        if random.random() < 0.8:  # 80%的概率添加referer
            # 对于其他页面，70%的概率使用同站点的首页作为来源
            if random.random() < 0.7:
                return f"{scheme}://{domain}/"
            # 30%的概率使用搜索引擎作为来源
            search_engines = [
                "https://www.google.com/search?q=",
                "https://www.bing.com/search?q=",
                "https://www.baidu.com/s?wd=",
            ]
            return random.choice(search_engines) + domain
        return None

    def process_request(self, request, spider):
        """处理请求，添加定制请求头"""
        # 从URL中提取域名
        domain = self._get_site_domain(request.url)
        
        # 记录域名访问统计
        self.domain_stats[domain] = self.domain_stats.get(domain, 0) + 1
        
        # 选择一个随机的User-Agent
        user_agent = random.choice(self.user_agents)
        self.ua_usage_stats[user_agent] = self.ua_usage_stats.get(user_agent, 0) + 1
        
        # 首先添加默认通用请求头
        # 随机选择 User-Agent
        request.headers['User-Agent'] = user_agent
        # 随机选择 Accept-Language
        accept_language = random.choice(self.accept_language)
        request.headers['Accept-Language'] = accept_language
        # 随机选择 Accept
        accept = random.choice(self.accept)
        request.headers['Accept'] = accept
        
        # 添加其他常用请求头
        request.headers.update({
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
        
        # 检查是否存在特定网站的请求头配置
        site_specific_used = False
        for site_domain, headers_template in self.site_specific_templates.items():
            if site_domain in domain:
                # 克隆模板以避免修改原始模板
                headers = headers_template.copy()
                
                # 如果是豆瓣，添加动态参数
                if site_domain == 'douban.com':
                    # 从URL中提取路径
                    from urllib.parse import urlparse
                    parsed_url = urlparse(request.url)
                    request_path = parsed_url.path
                    
                    # 添加与请求相关的动态参数
                    headers.update({
                        "authority": domain,
                        "method": request.method,
                        "path": request_path,
                        "scheme": "https",
                        "cookie": generate_random_cookie(),
                        "cache-control": random.choice(["max-age=0", "no-cache"]),
                        "priority": random.choice(["u=0, i", "u=1, i"]),
                    })
                
                # 使用特定网站的请求头
                request.headers.update(headers)
                site_specific_used = True
                print(f"【UA中间件】为域名 {domain} 使用特定请求头配置")
                break
        
        # 添加指纹防护请求头
        use_fingerprint = random.random() < 0.9  # 90%的概率添加浏览器指纹相关头
        if use_fingerprint:
            fingerprint_headers = self._get_browser_fingerprint_headers()
            request.headers.update(fingerprint_headers)
        
        # 添加Referer
        referer_added = False
        if 'Referer' not in request.headers:
            referer = self._get_referrer(request.url)
            if referer:
                request.headers['Referer'] = referer
                referer_added = True
        
        # 随机添加一些Cookie
        cookie_added = False
        if random.random() < 0.7 and 'Cookie' not in request.headers:  # 70%的概率添加Cookie
            cookie = self._get_random_cookie()
            request.headers['Cookie'] = cookie
            cookie_added = True
        
        # 针对AJAX请求特殊处理
        is_ajax = request.meta.get('is_ajax', False)
        if is_ajax:
            request.headers.update({
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
            })
        
        # 针对图片和资源请求特殊处理
        is_resource = request.meta.get('is_resource', False)
        if is_resource:
            request.headers.update({
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
            })
        
        # 随机设置屏幕分辨率和色深
        extra_headers_added = False
        if random.random() < 0.5:  # 50%的概率添加
            resolution = random.choice(self.screen_resolutions)
            width, height = resolution.split('x')
            color_depth = random.choice([24, 30, 32])
            
            headers_js = {
                'Sec-CH-UA-Bitness': random.choice(['64', '32']),
                'Sec-CH-UA-Arch': random.choice(['x86', 'arm']),
                'Sec-CH-UA-Full-Version': f'"{random.choice(self.chrome_versions)}.0.{random.randint(1000, 9999)}.{random.randint(10, 99)}"',
                'Sec-CH-UA-Platform-Version': f'"{random.randint(10, 14)}.{random.randint(0, 9)}.{random.randint(10000, 99999)}"',
                'Sec-CH-UA-Model': '""',
                'Sec-CH-UA-WoW64': random.choice(['?0', '?1']),
            }
            request.headers.update(headers_js)
            extra_headers_added = True

        # 输出调试信息
        print(f"\n【UA中间件】请求 URL: {request.url[:50]}...")
        print(f"【UA中间件】域名: {domain} (访问次数: {self.domain_stats.get(domain, 0)})")
        print(f"【UA中间件】User-Agent: {user_agent[:50]}...")
        print(f"【UA中间件】特定站点配置: {'是' if site_specific_used else '否'}")
        print(f"【UA中间件】添加指纹保护: {'是' if use_fingerprint else '否'}")
        print(f"【UA中间件】添加Referer: {'是' if referer_added else '否'}")
        print(f"【UA中间件】添加Cookie: {'是' if cookie_added else '否'}")
        print(f"【UA中间件】AJAX请求: {'是' if is_ajax else '否'}")
        print(f"【UA中间件】资源请求: {'是' if is_resource else '否'}")
        print(f"【UA中间件】添加额外headers: {'是' if extra_headers_added else '否'}")
        
        # 每50个请求输出一次统计信息
        request_count = sum(self.domain_stats.values())
        if request_count % 50 == 0:
            self._print_stats()

        return None
        
    def _print_stats(self):
        """打印中间件统计信息"""
        if not self.debug:
            return
            
        print("\n==== 请求头中间件统计 ====")
        print("-- 域名访问统计 --")
        # 根据访问次数排序
        sorted_domains = sorted(self.domain_stats.items(), key=lambda x: x[1], reverse=True)
        for domain, count in sorted_domains[:5]:  # 只显示前5个
            print(f"域名: {domain} - 访问: {count}次")
            
        print("\n-- User-Agent使用统计 --")
        # 根据使用次数排序
        sorted_uas = sorted(self.ua_usage_stats.items(), key=lambda x: x[1], reverse=True)
        for ua, count in sorted_uas[:3]:  # 只显示前3个
            print(f"UA: {ua[:50]}... - 使用: {count}次")
            
        total_requests = sum(self.domain_stats.values())
        print(f"\n总请求数: {total_requests}")
        print("=========================\n")


class DoubanDownloaderMiddleware:
    """豆瓣网站下载中间件，处理响应内容"""
    
    @classmethod
    def from_crawler(cls, crawler):
        """从settings获取设置"""
        return cls()
        
    def process_request(self, request, spider):
        """处理请求，添加必要的请求头和标记"""
        # 仅处理豆瓣的请求
        if spider.name == 'douban' and 'douban.com' in request.url:
            # 始终添加高质量请求头
            request.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            })
            
            # 只对初始搜索页和主要详情页使用Selenium，避免对每个资源都创建新的浏览器实例
            if ('subject' in request.url and '/subject/' in request.url) or \
               ('search' in request.url and 'search_text=' in request.url) or \
               request.meta.get('force_selenium', False):
                
                # 避免重复标记
                if not request.meta.get('use_selenium'):
                    request.meta['use_selenium'] = True
                    spider.logger.info(f"设置请求使用Selenium: {request.url}")

        return None
        
    def process_response(self, request, response, spider):
        """处理响应，检查是否需要重试"""
        # 仅处理豆瓣的响应
        if spider.name == 'douban' and 'douban.com' in request.url:
            # 检查响应状态码
            if response.status != 200:
                spider.logger.warning(f"响应状态码异常: {response.status}, URL: {response.url}")
                # 标记使用Selenium重试，但添加force_selenium标记以避免滥用
                request.meta['force_selenium'] = True
                request.dont_filter = True
                return request
                
            # 检查内容类型
            content_type = response.headers.get('Content-Type', b'').decode('utf-8', 'ignore')
            if 'text/html' not in content_type.lower() and ('subject' in request.url or 'search' in request.url):
                spider.logger.warning(f"响应内容类型异常: {content_type}, URL: {response.url}")
                # 只有对重要页面才使用Selenium重试
                request.meta['force_selenium'] = True
                request.dont_filter = True
                return request
            
            # 检查响应内容长度，只对主要页面执行此检查
            if ('subject' in request.url or 'search' in request.url) and len(response.body) < 1000:
                spider.logger.warning(f"响应内容过短({len(response.body)}字节), 可能是被反爬: {response.url}")
                request.meta['force_selenium'] = True
                request.dont_filter = True
                return request
                
        return response
        
    def process_exception(self, request, exception, spider):
        """处理异常"""
        if spider.name == 'douban':
            spider.logger.error(f"请求异常: {exception}, URL: {request.url}")
            # 只对重要的URL使用Selenium重试
            if 'subject' in request.url or 'search' in request.url:
                request.meta['force_selenium'] = True
                request.dont_filter = True
                return request
        return None


def generate_random_cookie():
    """
    生成随机豆瓣cookie
    以真实豆瓣cookie为模板，生成随机但合理的cookie值
    """
    import time
    import random
    import string
    
    # 基础时间戳：最近30天内的随机时间
    now = int(time.time())
    recent_timestamps = [
        now - random.randint(0, 30 * 24 * 60 * 60)  # 30天内的随机时间
        for _ in range(5)  # 生成5个不同的时间戳
    ]
    
    # 生成随机的bid值（豆瓣用户浏览器标识）
    chars = string.ascii_letters + string.digits
    bid = ''.join(random.choice(chars) for _ in range(11))
    
    # 随机的用户位置代码，中国常见城市代码
    locations = ["108288", "108296", "108090", "108303", "108289", "108304", "108307"]
    location = random.choice(locations)
    
    # 随机的推送消息数量
    push_noty_num = random.randint(0, 5)
    push_doumail_num = random.randint(0, 3)
    
    # 随机的utmz值以及utmcsr来源网站
    utmcsr_sites = ["baidu.com", "bing.com", "google.com", "douban.com", "weibo.com"]
    utmcsr = random.choice(utmcsr_sites)
    
    # 随机的Google Analytics ID
    ga_id = f"GA1.2.{random.randint(1000000000, 9999999999)}.{recent_timestamps[0]}"
    
    # 构建完整cookie字符串，结构与真实豆瓣cookie一致
    cookie_parts = [
        f"bid={bid}",
        f"_pk_id.100001.8cb4={random.randint(10000000, 99999999)}.{recent_timestamps[1]}",
        f'll="{location}"',
        f"push_noty_num={push_noty_num}",
        f"push_doumail_num={push_doumail_num}",
        f"__utmc={random.randint(10000000, 99999999)}",
        f"_vwo_uuid_v2={bid.upper()}{random.randint(10000, 99999)}{random.choice(chars).upper()}|{bid.lower()}",
        "douban-fav-remind=1",
        f"__utmv={random.randint(10000000, 99999999)}.{random.randint(10000, 99999)}",
        f"__yadk_uid={bid}{bid[:5]}",
        "ct=y",
        f"_ga={ga_id}",
        f"_ga_Y4GN1R87RG=GS1.1.{recent_timestamps[2]}.1.1.{recent_timestamps[2] + random.randint(60, 600)}.0.0.0",
        f"__utmz={random.randint(10000000, 99999999)}.{random.randint(1, 20)}.{random.randint(1, 10)}.{random.randint(1, 5)}.utmcsr={utmcsr}|utmccn=(referral)|utmcmd=referral|utmcct=/{''.join(random.choice(chars) for _ in range(8))}/",
        f"__utma={random.randint(10000000, 99999999)}.{random.randint(1000000000, 9999999999)}.{recent_timestamps[3]}.{recent_timestamps[3] + 86400}.{recent_timestamps[4]}.{random.randint(5, 30)}",
        f"_pk_ref.100001.8cb4=%5B%22%22%2C%22%22%2C{now}%2C%22https%3A%2F%2Fmovie.douban.com%2Fsubject%2F{random.randint(1000000, 9999999)}%2F%22%5D",
        "_pk_ses.100001.8cb4=1",
        f"ap_v=0,{random.randint(6, 9)}.0"
    ]
    
    # 随机决定是否包含某些cookie项
    if random.random() < 0.3:  # 30%的几率不包含某些可选cookie
        optional_indices = [5, 6, 7, 8, 9, 10, 12, 15]  # 可选cookie的索引
        for i in sorted(random.sample(optional_indices, random.randint(1, 3)), reverse=True):
            if i < len(cookie_parts):
                cookie_parts.pop(i)
    
    # 将所有部分组合成最终cookie字符串
    return "; ".join(cookie_parts)
