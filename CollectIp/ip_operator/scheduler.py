import threading
import time
import logging
from django.conf import settings
from .services.crawler import start_crawl
from .services.scorer import start_score

logger = logging.getLogger(__name__)

class IPPoolScheduler(threading.Thread):
    """IP池调度器"""
    
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.last_crawl_time = 0
        self.running = True
        # 从settings获取配置
        self.crawler_interval = settings.IP_POOL_CONFIG['CRAWLER_INTERVAL']
        self.score_interval = settings.IP_POOL_CONFIG['SCORE_INTERVAL']
    
    def run(self):
        while self.running:
            try:
                # 检查是否需要执行爬虫任务
                current_time = time.time()
                if current_time - self.last_crawl_time >= self.crawler_interval:  # 1小时间隔
                    logger.info("开始执行爬虫任务...")
                    if start_crawl():
                        self.last_crawl_time = current_time
                        logger.info("爬虫任务完成")
                    else:
                        logger.error("爬虫任务失败")
                
                # 执行评分任务
                logger.info("开始执行评分任务...")
                if start_score():
                    logger.info("评分任务完成")
                else:
                    logger.error("评分任务失败")
                
                # 等待下一轮
                time.sleep(self.score_interval)  # 30分钟检查一次
                
            except Exception as e:
                logger.error(f"调度器发生错误: {e}")
                time.sleep(300)  # 发生错误后等待5分钟

def start():
    """启动调度器"""
    scheduler = IPPoolScheduler()
    scheduler.start()
    logger.info("IP池调度器已启动")

def update_intervals(crawler_interval, score_interval):
    """更新调度器的时间间隔"""
    from django.conf import settings
    
    # 更新配置
    settings.IP_POOL_CONFIG.update({
        'CRAWLER_INTERVAL': crawler_interval,
        'SCORE_INTERVAL': score_interval,
    })
    
    # 获取调度器实例并更新间隔
    scheduler = IPPoolScheduler.get_instance()
    if scheduler:
        scheduler.crawler_interval = crawler_interval
        scheduler.score_interval = score_interval
        logger.info(f"调度器间隔已更新: 爬虫={crawler_interval}秒, 评分={score_interval}秒") 