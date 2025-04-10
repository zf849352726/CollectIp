import logging
from django.conf import settings
import sys
import os
import time
import threading
from datetime import datetime, timedelta

from .tasks import crawl_ip_task, score_ip_task, crawl_douban_task

logger = logging.getLogger('scheduler')

class SimpleJob:
    """简单的任务类"""
    
    def __init__(self, func, interval, job_id, args=None, kwargs=None):
        self.func = func
        self.interval = interval  # 间隔秒数
        self.job_id = job_id
        self.args = args or []
        self.kwargs = kwargs or {}
        self.last_run = None
        self.next_run = datetime.now()
    
    def should_run(self):
        """检查是否应该运行"""
        return datetime.now() >= self.next_run
    
    def run(self):
        """运行任务"""
        self.last_run = datetime.now()
        self.next_run = self.last_run + timedelta(seconds=self.interval)
        try:
            return self.func(*self.args, **self.kwargs)
        except Exception as e:
            logger.error(f"任务 {self.job_id} 执行出错: {e}")
            return None

class SimpleScheduler(threading.Thread):
    """简单的调度器实现"""
    
    def __init__(self):
        super().__init__(daemon=True)
        self.jobs = {}
        self.running = False
        self.lock = threading.Lock()
        self.logger = logger
    
    def add_job(self, func, interval, job_id, args=None, kwargs=None, replace_existing=True):
        """添加任务"""
        with self.lock:
            if job_id in self.jobs and not replace_existing:
                return None
                
            job = SimpleJob(func, interval, job_id, args, kwargs)
            self.jobs[job_id] = job
            self.logger.info(f"添加任务: {job_id}, 间隔: {interval}秒")
            return job
    
    def remove_job(self, job_id):
        """移除任务"""
        with self.lock:
            if job_id in self.jobs:
                self.logger.info(f"移除任务: {job_id}")
                del self.jobs[job_id]
                return True
            return False
    
    def run(self):
        """运行调度器主循环"""
        self.running = True
        self.logger.info("调度器启动")
        
        while self.running:
            with self.lock:
                now = datetime.now()
                for job_id, job in list(self.jobs.items()):
                    if job.should_run():
                        self.logger.info(f"执行任务: {job_id}")
                        job.run()
            
            # 睡眠1秒
            time.sleep(1)
    
    def shutdown(self):
        """关闭调度器"""
        self.running = False
        self.logger.info("调度器关闭")

class IPScheduler:
    """IP爬虫调度器"""
    
    _instance = None
    _initialized = False
    
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
        
        # 初始化简单调度器
        self._scheduler = SimpleScheduler()
        
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
            
            # 添加定时任务
            job = self._scheduler.add_job(
                self.start_crawl,
                interval=self.crawl_interval,
                job_id="ip_crawl",
                args=["all"],
                replace_existing=True,
            )
            
            self.crawl_job_id = "ip_crawl"
            self.logger.info(f"添加IP爬取任务成功: {self.crawl_job_id}, 间隔: {self.crawl_interval}秒")
            
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
                
            # 添加定时任务
            job = self._scheduler.add_job(
                self.start_score,
                interval=self.score_interval,
                job_id="ip_score",
                replace_existing=True,
            )
            
            self.score_job_id = "ip_score"
            self.logger.info(f"添加IP评分任务成功: {self.score_job_id}, 间隔: {self.score_interval}秒")
            
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