# Scrapy settings for crawl_ip project

BOT_NAME = 'crawl_ip'

# 修改spider路径
SPIDER_MODULES = ['crawl_ip.spiders']
NEWSPIDER_MODULE = 'crawl_ip.spiders'

# 其他Scrapy设置...
ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 16
DOWNLOAD_DELAY = 2
COOKIES_ENABLED = False

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# 修改pipeline路径
ITEM_PIPELINES = {
   'crawl_ip.pipelines.CrawlIpPipeline': 300,
} 