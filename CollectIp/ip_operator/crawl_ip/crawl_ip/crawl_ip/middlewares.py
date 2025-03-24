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
        self.blacklist = set()
        self.update_interval = 300
        self.last_update_time = 0
        # 创建IPScorer实例
        self.scorer = IPScorer()
        
    @classmethod
    def from_crawler(cls, crawler):
        """从settings获取数据库配置"""
        if not crawler.settings.getbool('PROXY_ENABLED'):
            raise NotConfigured
            
        return cls(
            db_host=crawler.settings.get('MYSQL_HOST'),
            db_user=crawler.settings.get('MYSQL_USER'),
            db_password=crawler.settings.get('MYSQL_PASSWORD'),
            db_name=crawler.settings.get('MYSQL_DATABASE')
        )
        
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
                        FROM ip_data 
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
                            SELECT server FROM ip_data 
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
            self.update_proxy_list()
        if self.proxy_list:
            return random.choice(self.proxy_list)
        return None
        
    def process_request(self, request, spider):
        """处理请求，添加代理"""
        proxy = self.get_random_proxy()
        if proxy:
            # 假设代理格式为 ip:port
            request.meta['proxy'] = f"http://{proxy}"
            spider.logger.debug(f'使用代理: {proxy}')
            
    def process_response(self, request, response, spider):
        """处理响应"""
        proxy = request.meta.get('proxy', '').replace('http://', '')
        
        if response.status != 200:
            if proxy:
                self.update_proxy_score(proxy, success=False)
                self.blacklist.add(proxy)
                spider.logger.warning(f'代理失败: {proxy}')
            
            # 重试请求
            request.dont_filter = True
            new_proxy = self.get_random_proxy()
            if new_proxy:
                request.meta['proxy'] = f"http://{new_proxy}"
            return request
        else:
            # 请求成功，更新代理评分
            if proxy:
                self.update_proxy_score(proxy, success=True)
        
        return response
        
    def process_exception(self, request, exception, spider):
        """处理异常"""
        proxy = request.meta.get('proxy', '').replace('http://', '')
        if proxy:
            self.update_proxy_score(proxy, success=False)
            self.blacklist.add(proxy)
            spider.logger.warning(f'代理异常: {proxy}, 异常: {exception}')
        
        # 重试请求
        request.dont_filter = True
        new_proxy = self.get_random_proxy()
        if new_proxy:
            request.meta['proxy'] = f"http://{new_proxy}"
        return request


class RandomUserAgentMiddleware:
    """随机请求头中间件"""
    
    def __init__(self):
        self.user_agents = [
            # Windows + Chrome
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            # Windows + Firefox
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
            # Windows + Edge
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
            # MacOS + Chrome
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # MacOS + Safari
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            # iOS + Safari
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            # Android + Chrome
            'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        ]
        
        self.accept_language = [
            'zh-CN,zh;q=0.9,en;q=0.8',
            'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'en-US,en;q=0.9,zh-CN;q=0.8',
            'en-GB,en;q=0.9',
            'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
        ]
        
        self.accept = [
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
        ]

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        # 随机选择 User-Agent
        request.headers['User-Agent'] = random.choice(self.user_agents)
        # 随机选择 Accept-Language
        request.headers['Accept-Language'] = random.choice(self.accept_language)
        # 随机选择 Accept
        request.headers['Accept'] = random.choice(self.accept)
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
        
        # 随机添加一些额外的请求头
        if random.random() < 0.3:  # 30%的概率添加额外请求头
            extra_headers = {
                'DNT': '1',
                'Sec-CH-UA': '" Not A;Brand";v="99", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-CH-UA-Mobile': '?0',
                'Sec-CH-UA-Platform': '"Windows"',
            }
            request.headers.update(extra_headers)

        return None
