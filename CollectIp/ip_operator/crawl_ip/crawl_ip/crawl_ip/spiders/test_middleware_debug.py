import scrapy
import logging
import os
import sys

# 配置日志
logger = logging.getLogger("test_middleware_spider")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class TestMiddlewareSpider(scrapy.Spider):
    name = "test_middleware"
    allowed_domains = ["httpbin.org"]
    start_urls = ["https://httpbin.org/get"]
    
    # 自定义设置
    custom_settings = {
        'LOG_LEVEL': 'DEBUG',
        'LOG_FORMAT': '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        'PROXY_DEBUG': True,
        'UA_DEBUG': True,
        'LOG_STDOUT': True,
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'crawl_ip.middlewares.RandomUserAgentMiddleware': 543,
            'crawl_ip.middlewares.ProxyMiddleware': 750,
        }
    }
    
    def __init__(self, *args, **kwargs):
        super(TestMiddlewareSpider, self).__init__(*args, **kwargs)
        print("\n\n【测试爬虫】初始化完成，即将发送测试请求...")
        print("【测试爬虫】此爬虫将发送请求到httpbin.org以测试中间件调试信息")
        
    def parse(self, response):
        print("\n【测试爬虫】收到响应，状态码:", response.status)
        print("【测试爬虫】请检查上方是否有UA中间件和代理中间件的调试输出")
        print("【测试爬虫】如果没有，可能是中间件未被正确初始化或调试信息被抑制")
        
        # 尝试解析返回的头信息
        try:
            data = response.json()
            if 'headers' in data:
                user_agent = data['headers'].get('User-Agent', '未设置')
                print(f"【测试爬虫】服务器接收到的User-Agent: {user_agent}")
            if 'origin' in data:
                origin_ip = data['origin']
                print(f"【测试爬虫】服务器看到的IP地址: {origin_ip}")
        except Exception as e:
            print(f"【测试爬虫】解析响应失败: {e}")
            
        # 生成第二个请求以测试中间件是否对每个请求都生效
        yield scrapy.Request(
            url="https://httpbin.org/user-agent",
            callback=self.parse_user_agent
        )
        
    def parse_user_agent(self, response):
        print("\n【测试爬虫】第二个请求完成，状态码:", response.status)
        try:
            data = response.json()
            if 'user-agent' in data:
                print(f"【测试爬虫】第二个请求的User-Agent: {data['user-agent']}")
        except Exception as e:
            print(f"【测试爬虫】解析第二个响应失败: {e}")
            
        print("\n【测试爬虫】调试测试完成")

# 直接运行脚本测试
if __name__ == "__main__":
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl(TestMiddlewareSpider)
    process.start() 