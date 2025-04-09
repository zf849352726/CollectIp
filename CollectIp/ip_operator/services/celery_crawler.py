"""
Celery爬虫服务接口
该服务使用Celery+Redis来管理和运行爬虫任务
"""

import os
import logging
import redis
import json
from django.conf import settings
from ..tasks import crawl_ip_task, crawl_douban_task

# 设置日志
logger = logging.getLogger('ip_operator')

# 创建Redis连接
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD
    )
    redis_available = True
except Exception as e:
    logger.error(f"Redis连接失败: {str(e)}")
    redis_available = False

def get_crawler_status(spider_name, params=None):
    """
    获取爬虫运行状态
    
    Args:
        spider_name: 爬虫名称
        params: 爬虫参数
    
    Returns:
        bool: 爬虫是否正在运行
    """
    if not redis_available:
        logger.warning("Redis不可用，无法获取爬虫状态")
        return False
    
    from ..tasks import generate_lock_key
    
    lock_key = generate_lock_key(spider_name, params)
    return redis_client.exists(lock_key)

def get_all_running_spiders():
    """
    获取所有正在运行的爬虫
    
    Returns:
        list: 正在运行的爬虫列表
    """
    if not redis_available:
        logger.warning("Redis不可用，无法获取运行中的爬虫")
        return []
    
    running_spiders = []
    for key in redis_client.keys("spider_lock:*"):
        key = key.decode('utf-8')
        parts = key.split(':', 2)
        if len(parts) >= 2:
            spider_info = {
                'name': parts[1],
            }
            if len(parts) > 2:
                try:
                    params = json.loads(parts[2])
                    spider_info['params'] = params
                except:
                    pass
            running_spiders.append(spider_info)
    
    return running_spiders

def start_crawl_ip(crawl_type="all"):
    """
    启动IP代理爬虫
    
    Args:
        crawl_type: 爬取类型，可选值：all, http, https 等
    
    Returns:
        task: Celery任务对象
    """
    # 检查爬虫是否已经在运行
    params = {'crawl_type': crawl_type}
    if get_crawler_status('collectip', params):
        logger.warning(f"IP爬虫已在运行中，跳过本次任务")
        return None
    
    logger.info(f"启动IP爬虫，类型: {crawl_type}")
    
    # 启动Celery任务
    task = crawl_ip_task.delay(crawl_type=crawl_type)
    
    logger.info(f"IP爬虫任务已提交，任务ID: {task.id}")
    return task

def start_crawl_douban(movie_name, strategy="sequential", max_pages=2, **kwargs):
    """
    启动豆瓣电影评论爬虫
    
    Args:
        movie_name: 电影名称
        strategy: 爬取策略
        max_pages: 最大爬取页数
        **kwargs: 其他爬虫参数
    
    Returns:
        task: Celery任务对象
    """
    if not movie_name:
        logger.error("电影名称不能为空")
        return None
    
    # 构建完整参数
    params = {
        'movie_name': movie_name,
        'strategy': strategy,
        'max_pages': max_pages
    }
    params.update(kwargs)
    
    # 检查爬虫是否已经在运行
    if get_crawler_status('douban_spider', params):
        logger.warning(f"豆瓣爬虫已在运行中，跳过本次任务: {movie_name}")
        return None
    
    logger.info(f"启动豆瓣爬虫，电影: {movie_name}, 策略: {strategy}")
    
    # 启动Celery任务
    task = crawl_douban_task.delay(
        movie_name=movie_name,
        strategy=strategy,
        max_pages=max_pages,
        **kwargs
    )
    
    logger.info(f"豆瓣爬虫任务已提交，任务ID: {task.id}")
    return task

def check_task_status(task_id):
    """
    检查任务状态
    
    Args:
        task_id: Celery任务ID
    
    Returns:
        str: 任务状态
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id)
    return {
        'id': task_id,
        'status': result.status,
        'result': result.result if result.ready() else None
    }

def stop_running_spider(spider_name, params=None):
    """
    停止正在运行的爬虫
    
    Args:
        spider_name: 爬虫名称
        params: 爬虫参数
    
    Returns:
        bool: 是否成功停止
    """
    if not redis_available:
        logger.warning("Redis不可用，无法停止爬虫")
        return False
    
    from ..tasks import release_spider_lock
    
    # 释放锁
    release_spider_lock(spider_name, params)
    
    # 尝试查找并终止对应的爬虫进程
    import psutil
    import signal
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.cmdline()).lower()
            if 'scrapy' in cmdline and 'crawl' in cmdline and spider_name.lower() in cmdline:
                logger.warning(f"尝试终止爬虫进程: PID={proc.pid}")
                os.kill(proc.pid, signal.SIGTERM)
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as e:
            continue
    
    return True 