# -*- coding: utf-8 -*-

# Scrapy settings for crawl_ip project

from importlib import reload
import os
import sys

# 将系统路径调整为能找到Django项目
# 获取爬虫项目目录的父级目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
# 添加到Python路径
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'CollectIp'))

# 设置Django设置模块
os.environ['DJANGO_SETTINGS_MODULE'] = 'CollectIp.settings_optimized'

# 其他Scrapy设置...
BOT_NAME = 'crawl_ip'

SPIDER_MODULES = ['crawl_ip.spiders']
NEWSPIDER_MODULE = 'crawl_ip.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy
CONCURRENT_REQUESTS = 4

# 添加下载延迟以减轻服务器负担
DOWNLOAD_DELAY = 3

# 其他爬虫设置...

# 禁用cookie
COOKIES_ENABLED = False

# 启用或禁用爬虫中间件
SPIDER_MIDDLEWARES = {
   # 'crawl_ip.middlewares.CrawlIpSpiderMiddleware': 543,
}

# 启用或禁用下载中间件
DOWNLOADER_MIDDLEWARES = {
   # 'crawl_ip.middlewares.CrawlIpDownloaderMiddleware': 543,
}

# 设置项目管道
ITEM_PIPELINES = {
   'crawl_ip.pipelines.IpPipeline': 300,
}

# 设置日志级别
LOG_LEVEL = 'INFO'

# 配置日志文件
LOG_FILE = os.path.join(BASE_DIR, 'logs/scrapy_collectip.log')

# 延迟Django设置初始化到爬虫运行时
# (不要在settings.py中调用django.setup())

# 使爬虫输出中文不出现乱码
FEED_EXPORT_ENCODING = 'utf-8'

# 爬虫行为配置
USER_AGENT = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36'

# 减少并发请求数以降低内存使用
CONCURRENT_REQUESTS_PER_DOMAIN = 2
CONCURRENT_REQUESTS_PER_IP = 2

# 禁用Telnet控制台以减少内存使用
TELNETCONSOLE_ENABLED = False

# 减少中间件数量以降低内存占用
SPIDER_MIDDLEWARES = {
   'crawl_ip.middlewares.CrawlIpSpiderMiddleware': 543,
}

DOWNLOADER_MIDDLEWARES = {
   'crawl_ip.middlewares.CrawlIpDownloaderMiddleware': 543,
   'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
}

# 禁用大多数扩展以减少内存使用
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
}

# 降低HTTP缓存大小以减少内存使用
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 400, 401, 403, 404, 408]
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# 优化下载处理
DOWNLOAD_TIMEOUT = 30
DOWNLOAD_MAXSIZE = 1024 * 1024  # 限制下载大小为1MB
DOWNLOAD_WARNSIZE = 32768  # 32KB

# 设置内存使用限制
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 128  # 限制爬虫内存使用
MEMUSAGE_WARNING_MB = 100

# 启用日志文件而不是控制台输出，并降低日志级别以减少磁盘IO
LOG_ENABLED = True
LOG_FILE_APPEND = False  # 每次运行覆盖日志文件以避免文件过大

# 禁用统计信息收集以减少内存使用
STATS_DUMP = False

# 使用更小的请求队列大小
SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue'
SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue'
SCHEDULER_PRIORITY_QUEUE = 'scrapy.pqueues.DownloaderAwarePriorityQueue'

# 关闭重试以减少请求数量
RETRY_ENABLED = False

