import threading
import time
import logging
import psutil
import os
from django.conf import settings
from .services.old_crawler import start_crawl, setup_logging
from .services.scorer import start_score

# 使用自定义日志设置，设置级别为WARNING
logger = setup_logging("ip_scheduler", logging.WARNING)

class IPPoolScheduler(threading.Thread):
    """IP池调度器"""
    
    _instance = None
    _lock = threading.Lock()  # 添加线程锁
    _running_flag_file = os.path.join(settings.BASE_DIR, 'scheduler_running.flag')
    
    @classmethod
    def get_instance(cls):
        return cls._instance
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(IPPoolScheduler, cls).__new__(cls)
            return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            super().__init__()
            self.daemon = True
            self.last_crawl_time = 0
            self.running = True
            self.initialized = True
            self.initial_delay = 300  # 启动后等待5分钟再执行第一次爬虫任务
            
            # 从settings获取配置
            self.crawler_interval = getattr(settings, 'IP_POOL_CONFIG', {}).get('CRAWLER_INTERVAL', 3600)
            self.score_interval = getattr(settings, 'IP_POOL_CONFIG', {}).get('SCORE_INTERVAL', 1800)
            self.auto_crawler = False  # 默认启用自动爬虫
            self.auto_score = False    # 默认启用自动评分
            
            # 尝试从数据库加载配置
            self.load_settings()
            
            IPPoolScheduler._instance = self
            
            # 创建运行标志文件
            with open(self._running_flag_file, 'w') as f:
                f.write(str(os.getpid()))
    
    def load_settings(self):
        """从数据库加载设置"""
        try:
            # 导入Django设置和模型
            import django
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CollectIp.settings')
            django.setup()
            
            # 导入ProxySettings模型
            from index.models import ProxySettings
            
            # 获取设置
            settings = ProxySettings.objects.first()
            if settings:
                logger.warning("从数据库加载调度器设置")
                self.crawler_interval = settings.crawler_interval
                self.score_interval = settings.score_interval
                self.auto_crawler = settings.auto_crawler
                self.auto_score = settings.auto_score
                logger.warning(f"调度器设置: 爬虫间隔={self.crawler_interval}秒, 评分间隔={self.score_interval}秒, "
                      f"自动爬虫={self.auto_crawler}, 自动评分={self.auto_score}")
            else:
                logger.warning("数据库中无设置，使用默认值")
        except Exception as e:
            logger.error(f"加载设置出错: {e}")
    
    def is_crawler_running(self):
        """检查是否有爬虫进程在运行"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # 检查是否是Python进程且命令行包含crawl_ip或collectip
                cmdline = ' '.join(proc.cmdline()).lower()
                if 'python' in proc.name().lower() and ('crawl_ip' in cmdline or 'collectip' in cmdline):
                    logger.warning(f"检测到正在运行的爬虫进程: PID={proc.pid}, 命令={cmdline}")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    
    def is_another_scheduler_running(self):
        """检查是否有其他调度器在运行"""
        try:
            if os.path.exists(self._running_flag_file):
                with open(self._running_flag_file, 'r') as f:
                    pid = int(f.read().strip())
                    if pid != os.getpid():
                        # 检查PID是否仍然活跃
                        try:
                            process = psutil.Process(pid)
                            if process.is_running() and 'python' in process.name().lower():
                                logger.warning(f"检测到另一个调度器实例在运行: PID={pid}")
                                return True
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            # PID不存在或无法访问，说明进程已经退出
                            pass
                
                # 更新标志文件为当前PID
                with open(self._running_flag_file, 'w') as f:
                    f.write(str(os.getpid()))
        except Exception as e:
            logger.error(f"检查其他调度器实例时出错: {e}")
            
        return False
    
    def check_settings_changed(self):
        """检查数据库设置是否有变化"""
        try:
            # 导入ProxySettings模型
            from index.models import ProxySettings
            
            # 获取最新设置
            settings = ProxySettings.objects.first()
            if settings:
                # 检查设置是否有变化
                if (self.crawler_interval != settings.crawler_interval or
                    self.score_interval != settings.score_interval or
                    self.auto_crawler != settings.auto_crawler or
                    self.auto_score != settings.auto_score):
                    
                    logger.warning("检测到设置变化，更新调度器设置")
                    self.crawler_interval = settings.crawler_interval
                    self.score_interval = settings.score_interval
                    self.auto_crawler = settings.auto_crawler
                    self.auto_score = settings.auto_score
                    logger.warning(f"新设置: 爬虫间隔={self.crawler_interval}秒, 评分间隔={self.score_interval}秒, "
                          f"自动爬虫={self.auto_crawler}, 自动评分={self.auto_score}")
                    return True
        except Exception as e:
            logger.error(f"检查设置变化时出错: {e}")
        
        return False
    
    def run(self):
        # 启动时等待一段时间，避免立即执行爬虫
        logger.warning(f"调度器已启动，将在{self.initial_delay}秒后执行第一次任务")
        time.sleep(self.initial_delay)
        
        while self.running:
            try:
                # 检查是否有其他调度器在运行
                if self.is_another_scheduler_running():
                    logger.warning("检测到另一个调度器实例，当前实例将停止")
                    self.running = False
                    break
                
                # 检查设置是否有变化
                self.check_settings_changed()
                
                current_time = time.time()
                
                # 检查是否需要执行爬虫任务
                if self.auto_crawler and current_time - self.last_crawl_time >= self.crawler_interval:
                    # 检查是否有爬虫进程在运行
                    if not self.is_crawler_running():
                        logger.warning("执行爬虫任务...")
                        if start_crawl():
                            self.last_crawl_time = current_time
                            logger.warning("爬虫任务完成")
                        else:
                            logger.error("爬虫任务失败")
                    else:
                        logger.warning("已有爬虫进程在运行，跳过本次任务")
                elif not self.auto_crawler:
                    logger.warning("自动爬虫已禁用，跳过爬虫任务")
                
                # 执行评分任务
                if self.auto_score:
                    try:
                        if start_score():
                            logger.warning("评分任务完成")
                        else:
                            logger.error("评分任务失败")
                    except Exception as e:
                        logger.error(f"评分任务出错: {e}")
                else:
                    logger.warning("自动评分已禁用，跳过评分任务")
                
                # 使用爬虫间隔作为等待时间
                wait_time = min(self.crawler_interval, self.score_interval)
                logger.warning(f"等待{wait_time}秒后执行下一轮任务")
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"调度器发生错误: {e}")
                time.sleep(300)  # 发生错误后等待5分钟
    
    def stop(self):
        """停止调度器"""
        self.running = False
        logger.warning("调度器停止中...")
        # 移除运行标志文件
        if os.path.exists(self._running_flag_file):
            try:
                os.remove(self._running_flag_file)
            except Exception as e:
                logger.error(f"移除调度器运行标志文件时出错: {e}")

def start():
    """启动调度器"""
    # 检查是否已经有调度器在运行
    if IPPoolScheduler.get_instance() is not None:
        logger.warning("调度器已经在运行中")
        return
        
    scheduler = IPPoolScheduler()
    
    # 检查是否有其他调度器实例在运行
    if scheduler.is_another_scheduler_running():
        logger.warning("已有其他调度器实例在运行，不再启动新实例")
        return
        
    scheduler.start()
    logger.warning("IP池调度器已启动")

def update_intervals(crawler_interval, score_interval, auto_crawler=None, auto_score=None):
    """更新调度器的时间间隔和自动任务设置"""
    # 获取调度器实例并更新间隔
    scheduler = IPPoolScheduler.get_instance()
    if scheduler:
        scheduler.crawler_interval = crawler_interval
        scheduler.score_interval = score_interval
        
        # 如果提供了自动任务参数，也更新它们
        if auto_crawler is not None:
            scheduler.auto_crawler = auto_crawler
        if auto_score is not None:
            scheduler.auto_score = auto_score
            
        logger.warning(f"调度器设置已更新: 爬虫间隔={crawler_interval}秒, 评分间隔={score_interval}秒, "
                 f"自动爬虫={scheduler.auto_crawler}, 自动评分={scheduler.auto_score}")
    else:
        # 如果调度器未启动，更新配置
        try:
            settings.IP_POOL_CONFIG.update({
                'CRAWLER_INTERVAL': crawler_interval,
                'SCORE_INTERVAL': score_interval,
            })
            logger.warning("已更新配置，但调度器未启动")
        except Exception as e:
            logger.error(f"更新配置失败: {e}")

def is_scheduler_running():
    """检查调度器是否在运行"""
    return IPPoolScheduler.get_instance() is not None and IPPoolScheduler.get_instance().is_alive() 