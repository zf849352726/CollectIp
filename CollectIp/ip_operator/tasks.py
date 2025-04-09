import os
import sys
import json
import logging
import subprocess
import traceback
from celery import shared_task
from django.conf import settings
from pathlib import Path
import redis

# 创建Redis连接
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD
)

# 设置日志
logger = logging.getLogger('task_logger')

def get_crawler_dir():
    """获取爬虫目录路径"""
    base_dir = settings.BASE_DIR
    crawler_dir = os.path.join(base_dir, 'CollectIp', 'ip_operator', 'crawl_ip', 'crawl_ip')
    if os.path.exists(crawler_dir):
        return crawler_dir
    
    # 尝试备用路径
    alternate_dir = os.path.join(base_dir, 'ip_operator', 'crawl_ip', 'crawl_ip')
    if os.path.exists(alternate_dir):
        return alternate_dir
    
    # 寻找任何包含crawl_ip的目录
    for root, dirs, files in os.walk(base_dir):
        if 'crawl_ip' in dirs:
            potential_dir = os.path.join(root, 'crawl_ip')
            if os.path.exists(os.path.join(potential_dir, 'settings.py')):
                return potential_dir
    
    logger.error("无法找到爬虫目录")
    return None

def generate_lock_key(spider_name, params=None):
    """生成任务锁的键名"""
    if params:
        # 将参数转换为排序后的字符串，确保相同参数生成相同的键
        params_str = json.dumps(params, sort_keys=True)
        return f"spider_lock:{spider_name}:{params_str}"
    return f"spider_lock:{spider_name}"

def is_spider_running(spider_name, params=None):
    """检查爬虫是否正在运行"""
    lock_key = generate_lock_key(spider_name, params)
    return redis_client.exists(lock_key)

def set_spider_lock(spider_name, params=None, timeout=3600):
    """设置爬虫运行锁"""
    lock_key = generate_lock_key(spider_name, params)
    return redis_client.set(lock_key, "1", ex=timeout, nx=True)

def release_spider_lock(spider_name, params=None):
    """释放爬虫运行锁"""
    lock_key = generate_lock_key(spider_name, params)
    redis_client.delete(lock_key)

@shared_task(bind=True, max_retries=3)
def run_spider_task(self, spider_name, movie_name=None, crawl_type=None, **kwargs):
    """
    运行爬虫任务
    
    Args:
        spider_name: 爬虫名称
        movie_name: 电影名称（可选）
        crawl_type: 爬取类型（可选）
        **kwargs: 其他爬虫参数
    
    Returns:
        dict: 任务执行结果
    """
    # 生成任务参数
    params = {'movie_name': movie_name, 'crawl_type': crawl_type}
    params.update(kwargs)
    
    # 检查爬虫是否已在运行
    if is_spider_running(spider_name, params):
        logger.warning(f"爬虫 {spider_name} 已在运行中，跳过本次任务")
        return {'status': 'skipped', 'reason': 'already_running'}
    
    # 设置爬虫锁
    if not set_spider_lock(spider_name, params):
        logger.warning(f"无法获取爬虫 {spider_name} 的锁，可能已被其他进程获取")
        return {'status': 'skipped', 'reason': 'lock_failed'}
    
    try:
        # 获取爬虫目录
        crawler_dir = get_crawler_dir()
        if not crawler_dir:
            logger.error("无法找到爬虫目录")
            release_spider_lock(spider_name, params)
            return {'status': 'failed', 'reason': 'crawler_dir_not_found'}
        
        # 准备环境变量
        env = os.environ.copy()
        
        # 设置电影名称（如果有）
        if movie_name:
            # 编码中文名称防止问题
            import base64
            encoded_name = base64.b64encode(movie_name.encode('utf-8')).decode('ascii')
            env['MOVIE_NAME'] = movie_name
            env['MOVIE_NAME_ENCODED'] = encoded_name
            logger.debug(f"设置电影名称环境变量: {movie_name} (编码: {encoded_name})")
        
        # 设置爬取类型（如果有）
        if crawl_type:
            env['CRAWL_TYPE'] = crawl_type
            logger.debug(f"设置爬取类型环境变量: {crawl_type}")
        
        # 设置爬虫参数（如果有）
        if kwargs:
            env['CRAWL_CONFIG'] = json.dumps(kwargs)
            logger.debug(f"设置爬虫配置环境变量: {json.dumps(kwargs)}")
        
        # 构建命令
        cmd = [
            sys.executable,  # 当前Python解释器
            '-m', 'scrapy', 'crawl', spider_name
        ]
        
        # 添加命令行参数，使用-a传递Spider参数
        if movie_name:
            cmd.extend(['-a', f'movie="{movie_name}"'])
        if 'strategy' in kwargs:
            cmd.extend(['-a', f'strategy={kwargs["strategy"]}'])
        if 'max_pages' in kwargs:
            cmd.extend(['-a', f'max_pages={kwargs["max_pages"]}'])
        
        logger.info(f"开始运行爬虫: {' '.join(cmd)}")
        
        # 执行子进程
        process = subprocess.Popen(
            cmd,
            cwd=crawler_dir,  # 设置工作目录
            env=env,          # 设置环境变量
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True          # 以文本模式返回输出
        )
        
        # 等待进程完成
        stdout, stderr = process.communicate()
        
        # 记录输出
        if stdout:
            logger.debug(f"爬虫输出: {stdout[:1000]}...")
        if stderr:
            logger.warning(f"爬虫错误: {stderr}")
        
        # 检查返回码
        if process.returncode != 0:
            logger.error(f"爬虫进程返回非零状态码: {process.returncode}")
            return {
                'status': 'failed',
                'returncode': process.returncode,
                'stderr': stderr[:500] if stderr else None
            }
        
        logger.info(f"爬虫 {spider_name} 执行完成")
        return {
            'status': 'success',
            'returncode': process.returncode
        }
    
    except Exception as e:
        logger.error(f"执行爬虫任务时出错: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 任务重试
        if self.request.retries < self.max_retries:
            logger.info(f"任务将在60秒后重试，当前重试次数: {self.request.retries + 1}")
            self.retry(exc=e, countdown=60)
        
        return {
            'status': 'failed',
            'error': str(e)
        }
    
    finally:
        # 释放爬虫锁
        release_spider_lock(spider_name, params)
        logger.debug(f"已释放爬虫 {spider_name} 的锁")

@shared_task
def crawl_ip_task(crawl_type="all"):
    """
    爬取IP代理的任务
    
    Args:
        crawl_type: 爬取类型，可选值有 all, http, https 等
    """
    return run_spider_task.delay('collectip', crawl_type=crawl_type)

@shared_task
def crawl_douban_task(movie_name, strategy="sequential", max_pages=2, **kwargs):
    """
    爬取豆瓣电影评论的任务
    
    Args:
        movie_name: 电影名称
        strategy: 爬取策略，例如 sequential, random_pages, random_interval, random_block, random 等
        max_pages: 最大爬取页数
        **kwargs: 其他爬虫参数
    """
    params = {
        'strategy': strategy,
        'max_pages': max_pages
    }
    
    # 根据不同策略添加所需参数
    if strategy == 'random_pages':
        # 随机页码策略需要sample_size参数
        params['sample_size'] = kwargs.get('sample_size', 5)
    elif strategy == 'random_interval':
        # 随机间隔策略需要max_interval参数
        params['max_interval'] = kwargs.get('max_interval', 3)
    elif strategy == 'random_block':
        # 随机区块策略需要block_size参数
        params['block_size'] = kwargs.get('block_size', 3)
    elif strategy == 'random':
        # 随机策略可能需要所有参数，取决于随机选择的策略
        params['sample_size'] = kwargs.get('sample_size', 5)
        params['max_interval'] = kwargs.get('max_interval', 3)
        params['block_size'] = kwargs.get('block_size', 3)
    
    # 添加其他参数
    for key, value in kwargs.items():
        if key not in params:
            params[key] = value
    
    return run_spider_task.delay('douban_spider', movie_name=movie_name, **params) 