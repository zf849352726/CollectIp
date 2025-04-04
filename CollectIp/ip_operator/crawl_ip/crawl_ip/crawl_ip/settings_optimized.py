# -*- coding: utf-8 -*-

# Scrapy设置 - 内存优化版本
# 适用于内存有限的Linux VPS

BOT_NAME = 'crawl_ip'

SPIDER_MODULES = ['crawl_ip.spiders']
NEWSPIDER_MODULE = 'crawl_ip.spiders'

# 爬虫行为配置
USER_AGENT = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36'

# 遵守robots.txt规则
ROBOTSTXT_OBEY = True

# 减少并发请求数以降低内存使用
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2
CONCURRENT_REQUESTS_PER_IP = 2

# 下载延迟，增大以减少服务器负载和内存使用
DOWNLOAD_DELAY = 3

# 禁用cookies以减少内存使用
COOKIES_ENABLED = False

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

# 减少Item Pipeline使用
ITEM_PIPELINES = {
   'crawl_ip.pipelines.ProxyPipeline': 300,
   'crawl_ip.pipelines.CommentPipeline': 200,
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
LOG_LEVEL = 'WARNING'  # 只记录警告和错误
LOG_FILE = 'crawl_ip.log'
LOG_FILE_APPEND = False  # 每次运行覆盖日志文件以避免文件过大

# 禁用统计信息收集以减少内存使用
STATS_DUMP = False

# 使用更小的请求队列大小
SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue'
SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue'
SCHEDULER_PRIORITY_QUEUE = 'scrapy.pqueues.DownloaderAwarePriorityQueue'

# 减少每个域名和IP的请求数
CONCURRENT_REQUESTS_PER_DOMAIN = 2
CONCURRENT_REQUESTS_PER_IP = 2

# 关闭重试以减少请求数量
RETRY_ENABLED = False 