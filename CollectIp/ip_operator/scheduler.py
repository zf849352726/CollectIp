import logging
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
import sys
import os
from datetime import datetime

from .tasks import crawl_ip_task, score_ip_task, crawl_douban_task

logger = logging.getLogger('scheduler')

class IPScheduler:
    """IP爬虫调度器"""
    
    _instance = None
    _initialized = False
    _scheduler = None
    
    @classmethod
    def get_instance(cls):
        """单例模式获取实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初始化调度器"""
        if IPScheduler._initialized:
            return
            
        self.logger = logger
        self.logger.info("初始化IP爬虫调度器")
        
        # 从配置中读取调度设置
        self.settings = getattr(settings, 'IP_POOL_CONFIG', {})
        self.crawl_interval = self.settings.get('CRAWLER_INTERVAL', 3600)  # 默认每小时爬取一次
        self.score_interval = self.settings.get('SCORE_INTERVAL', 1800)    # 默认每30分钟评分一次
        self.auto_crawler = self.settings.get('AUTO_CRAWLER', True)        # 默认启用自动爬虫
        self.auto_score = self.settings.get('AUTO_SCORE', True)            # 默认启用自动评分
        
        # 初始化ApScheduler
        self._scheduler = BackgroundScheduler()
        self._scheduler.add_jobstore(DjangoJobStore(), "default")
        
        # 初始化任务状态
        self.crawl_job_id = None
        self.score_job_id = None
        
        IPScheduler._initialized = True
    
    def start(self):
        """启动调度器"""
        if self._scheduler.running:
            self.logger.warning("调度器已经在运行中")
            return
            
        self.logger.info("启动IP爬虫调度器")
        
        try:
            # 添加IP爬取任务
            if self.auto_crawler:
                self.add_crawl_job()
                
            # 添加IP评分任务
            if self.auto_score:
                self.add_score_job()
                
            # 启动调度器
            self._scheduler.start()
            self.logger.info("调度器启动成功")
        except Exception as e:
            self.logger.error(f"启动调度器失败: {e}")
    
    def stop(self):
        """停止调度器"""
        if not self._scheduler.running:
            self.logger.warning("调度器未运行")
            return
            
        self.logger.info("停止IP爬虫调度器")
        
        try:
            self._scheduler.shutdown()
            self.logger.info("调度器已停止")
        except Exception as e:
            self.logger.error(f"停止调度器失败: {e}")
    
    def add_crawl_job(self):
        """添加IP爬取任务"""
        try:
            # 先移除可能存在的旧任务
            if self.crawl_job_id:
                self._scheduler.remove_job(self.crawl_job_id)
                
            # 转换为cron表达式
            seconds = self.crawl_interval
            minutes = seconds // 60
            hours = minutes // 60
            
            if hours > 0:
                cron_expr = f"0 0 */{hours} * * *"  # 每x小时执行
            elif minutes > 0:
                cron_expr = f"0 */{minutes} * * * *"  # 每x分钟执行
            else:
                cron_expr = f"*/{seconds} * * * * *"  # 每x秒执行
                
            self.logger.info(f"设置IP爬取任务，Cron表达式: {cron_expr}")
            
            # 添加定时任务
            job = self._scheduler.add_job(
                self.start_crawl,
                trigger=CronTrigger.from_crontab(cron_expr),
                id="ip_crawl",
                max_instances=1,
                replace_existing=True,
            )
            
            self.crawl_job_id = job.id
            self.logger.info(f"添加IP爬取任务成功: {job.id}")
            
            # 立即执行一次
            self.start_crawl()
        except Exception as e:
            self.logger.error(f"添加IP爬取任务失败: {e}")
    
    def add_score_job(self):
        """添加IP评分任务"""
        try:
            # 先移除可能存在的旧任务
            if self.score_job_id:
                self._scheduler.remove_job(self.score_job_id)
                
            # 转换为cron表达式
            seconds = self.score_interval
            minutes = seconds // 60
            hours = minutes // 60
            
            if hours > 0:
                cron_expr = f"0 0 */{hours} * * *"  # 每x小时执行
            elif minutes > 0:
                cron_expr = f"0 */{minutes} * * * *"  # 每x分钟执行
            else:
                cron_expr = f"*/{seconds} * * * * *"  # 每x秒执行
                
            self.logger.info(f"设置IP评分任务，Cron表达式: {cron_expr}")
            
            # 添加定时任务
            job = self._scheduler.add_job(
                self.start_score,
                trigger=CronTrigger.from_crontab(cron_expr),
                id="ip_score",
                max_instances=1,
                replace_existing=True,
            )
            
            self.score_job_id = job.id
            self.logger.info(f"添加IP评分任务成功: {job.id}")
            
            # 立即执行一次
            self.start_score()
        except Exception as e:
            self.logger.error(f"添加IP评分任务失败: {e}")
    
    def start_crawl(self, crawl_type='all'):
        """启动IP爬取任务"""
        try:
            self.logger.info(f"启动IP爬取任务，类型: {crawl_type}")
            task = crawl_ip_task.delay(crawl_type)
            self.logger.info(f"IP爬取任务已提交，任务ID: {task.id}")
            return task.id
        except Exception as e:
            self.logger.error(f"启动IP爬取任务失败: {e}")
            return None
    
    def start_score(self):
        """启动IP评分任务"""
        try:
            self.logger.info("启动IP评分任务")
            task = score_ip_task.delay()
            self.logger.info(f"IP评分任务已提交，任务ID: {task.id}")
            return task.id
        except Exception as e:
            self.logger.error(f"启动IP评分任务失败: {e}")
            return None
            
    def start_douban_crawl(self, movie_name, strategy="sequential", max_pages=2, **kwargs):
        """启动豆瓣电影评论爬取任务"""
        try:
            self.logger.info(f"启动豆瓣电影评论爬取任务: {movie_name}")
            task = crawl_douban_task.delay(
                movie_name=movie_name, 
                strategy=strategy, 
                max_pages=max_pages, 
                **kwargs
            )
            self.logger.info(f"豆瓣爬取任务已提交，任务ID: {task.id}")
            return task.id
        except Exception as e:
            self.logger.error(f"启动豆瓣爬取任务失败: {e}")
            return None
    
    def update_settings(self, crawl_interval=None, score_interval=None, auto_crawler=None, auto_score=None):
        """更新调度设置"""
        if crawl_interval is not None:
            self.crawl_interval = crawl_interval
        if score_interval is not None:
            self.score_interval = score_interval
        if auto_crawler is not None:
            self.auto_crawler = auto_crawler
        if auto_score is not None:
            self.auto_score = auto_score
            
        self.logger.info(f"更新调度设置: 爬虫间隔={self.crawl_interval}秒, 评分间隔={self.score_interval}秒, "
                       f"自动爬虫={self.auto_crawler}, 自动评分={self.auto_score}")
        
        # 重新添加任务
        if self.auto_crawler:
            self.add_crawl_job()
        elif self.crawl_job_id:
            self._scheduler.remove_job(self.crawl_job_id)
            self.crawl_job_id = None
            
        if self.auto_score:
            self.add_score_job()
        elif self.score_job_id:
            self._scheduler.remove_job(self.score_job_id)
            self.score_job_id = None
    
    def is_running(self):
        """检查调度器是否运行中"""
        return self._scheduler.running if self._scheduler else False
        
# 辅助函数
def start():
    """启动调度器"""
    scheduler = IPScheduler.get_instance()
    scheduler.start()
    
def stop():
    """停止调度器"""
    scheduler = IPScheduler.get_instance()
    scheduler.stop()
    
def is_running():
    """检查调度器是否运行中"""
    scheduler = IPScheduler.get_instance()
    return scheduler.is_running()
    
def update_settings(crawl_interval=None, score_interval=None, auto_crawler=None, auto_score=None):
    """更新调度设置"""
    scheduler = IPScheduler.get_instance()
    scheduler.update_settings(
        crawl_interval=crawl_interval,
        score_interval=score_interval,
        auto_crawler=auto_crawler,
        auto_score=auto_score
    )
    
def start_crawl(crawl_type='all'):
    """启动IP爬取任务"""
    scheduler = IPScheduler.get_instance()
    return scheduler.start_crawl(crawl_type)
    
def start_score():
    """启动IP评分任务"""
    scheduler = IPScheduler.get_instance()
    return scheduler.start_score()
    
def start_douban_crawl(movie_name, strategy="sequential", max_pages=2, **kwargs):
    """启动豆瓣电影评论爬取任务"""
    scheduler = IPScheduler.get_instance()
    return scheduler.start_douban_crawl(
        movie_name=movie_name,
        strategy=strategy,
        max_pages=max_pages,
        **kwargs
    ) 