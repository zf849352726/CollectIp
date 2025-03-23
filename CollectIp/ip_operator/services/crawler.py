import os
import logging
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from django.conf import settings

logger = logging.getLogger(__name__)

def run_spider():
    """运行爬虫收集IP"""
    try:
        crawler_path = os.path.join(settings.BASE_DIR, 'ip_operator', 'crawl_ip')
        original_dir = os.getcwd()
        os.chdir(crawler_path)
        
        os.environ['SCRAPY_SETTINGS_MODULE'] = 'crawl_ip.settings'
        
        # 获取爬虫配置
        crawler_settings = settings.IP_POOL_CONFIG.get('CRAWLER', {})
        scrapy_settings = get_project_settings()
        
        # 更新Scrapy设置
        scrapy_settings.update({
            'USER_AGENT': crawler_settings.get('USER_AGENT'),
            'DOWNLOAD_DELAY': crawler_settings.get('DOWNLOAD_DELAY', 2),
            'CONCURRENT_REQUESTS': crawler_settings.get('CONCURRENT_REQUESTS', 16),
        })
        
        process = CrawlerProcess(scrapy_settings)
        process.crawl('collectip')
        process.start(stop_after_crawl=True)
        
        logger.info("爬虫任务执行完成")
        return True
    except Exception as e:
        logger.error(f"爬虫任务执行失败: {e}")
        return False
    finally:
        os.chdir(original_dir) 