# Scrapy settings for crawl_ip project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "crawl_ip"

SPIDER_MODULES = ["crawl_ip.spiders"]
NEWSPIDER_MODULE = "crawl_ip.spiders"

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = "crawl_ip (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    "crawl_ip.middlewares.CrawlIpSpiderMiddleware": 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'crawl_ip.middlewares.RandomUserAgentMiddleware': 543,
    'crawl_ip.middlewares.DoubanDownloaderMiddleware': 600,
    'crawl_ip.middlewares.ProxyMiddleware': 750,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'crawl_ip.pipelines.SaveIpPipeline': 300,
    'crawl_ip.pipelines.MoviePipeline': 400,
    'crawl_ip.pipelines.CommentPipeline': 500,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = "httpcache"
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.selectreactor.SelectReactor"
FEED_EXPORT_ENCODING = "utf-8"

# 将日志级别设置为INFO，确保调试信息可见
LOG_LEVEL = 'INFO'

# 日志格式化
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'

# 确保调试信息输出到控制台
LOG_STDOUT = True

# 启用代理中间件
PROXY_ENABLED = True
PROXY_DEBUG = True  # 启用代理中间件调试信息

# 启用请求头中间件调试信息
UA_DEBUG = True

# 增加超时设置，防止爬虫卡住
DOWNLOAD_TIMEOUT = 30
DNS_TIMEOUT = 15

# 关闭重定向
REDIRECT_ENABLED = False

# 降低重试次数
RETRY_TIMES = 2

# 关闭辅助日志，降低输出
LOG_FILE_APPEND = False
STATS_DUMP = False

# django接口
import sys
import os
import django
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent

# 添加必要的路径到Python搜索路径
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'CollectIp'))
sys.path.insert(0, str(PROJECT_ROOT / 'CollectIp' / 'ip_operator'))
sys.path.insert(0, str(PROJECT_ROOT / 'CollectIp' / 'ip_operator' / 'crawl_ip'))
sys.path.insert(0, str(PROJECT_ROOT / 'CollectIp' / 'ip_operator' / 'crawl_ip' / 'crawl_ip'))
sys.path.insert(0, str(PROJECT_ROOT / 'CollectIp' / 'ip_operator' / 'crawl_ip' / 'crawl_ip' / 'crawl_ip'))

# 设置Django环境
os.environ['DJANGO_SETTINGS_MODULE'] = 'CollectIp.settings'
django.setup()

# 数据库配置
MYSQL_HOST = '127.0.0.1'
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DATABASE = 'collectipdb'
PORT = '3306',

# 配置下载超时
DOWNLOAD_TIMEOUT = 120

# 配置重试
RETRY_ENABLED = True
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]

# 配置并发
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# 配置UserAgent
# USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# 增加Selenium相关配置
SELENIUM_DRIVER_NAME = 'chrome'
SELENIUM_DRIVER_EXECUTABLE_PATH = None  # 使用ChromeDriverManager自动管理
SELENIUM_DRIVER_ARGUMENTS = ['--disable-gpu', '--disable-blink-features=AutomationControlled']

# 豆瓣爬虫特定配置
DOUBAN_USE_SELENIUM = True

# MongoDB配置
MONGODB_CONN = {
    'host': 'localhost',
    'port': 27017,
    'db': 'collectip_comments',
    'collection': 'movie_comments',
    'username': '',  # 如果需要认证，填写用户名
    'password': ''   # 如果需要认证，填写密码
}
