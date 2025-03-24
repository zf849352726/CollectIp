from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import os
import sys
import logging
import django
from multiprocessing import Process
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 设置Django环境
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 添加项目根目录到Python路径
sys.path.insert(0, BASE_DIR)
# 添加Django项目目录到Python路径
DJANGO_PROJECT_DIR = os.path.join(BASE_DIR, 'CollectIp')
sys.path.insert(0, DJANGO_PROJECT_DIR)

# 记录路径信息
print(f"BASE_DIR: {BASE_DIR}")
print(f"DJANGO_PROJECT_DIR: {DJANGO_PROJECT_DIR}")
print(f"Python Path: {sys.path}")

# 只有在单独运行这个脚本时才初始化Django
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CollectIp.settings')
    django.setup()  # 初始化Django
else:
    # 确保设置了DJANGO_SETTINGS_MODULE环境变量
    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CollectIp.settings')

# 当前文件的父目录
CURRENT_DIR = Path(__file__).resolve().parent
# 项目根目录
PROJECT_ROOT = CURRENT_DIR.parent.parent.parent

# 设置日志
def setup_logging(name="ip_operator"):
    """设置日志配置"""
    logger = logging.getLogger(name)
    
    # 如果已经有处理器，不再添加新的处理器
    if logger.handlers:
        return logger
    
    # 确保日志目录存在
    log_dir = os.path.join(PROJECT_ROOT, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"{name}.log")
    
    try:
        # 尝试创建文件处理器
        handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8',
            delay=True  # 延迟创建文件，直到第一次写入
        )
    except PermissionError:
        # 如果文件被占用，使用时间戳创建一个新的日志文件
        timestamp = int(time.time())
        alt_log_file = os.path.join(log_dir, f"{name}_{timestamp}.log")
        try:
            handler = RotatingFileHandler(
                alt_log_file, 
                maxBytes=10*1024*1024,
                backupCount=5,
                encoding='utf-8',
                delay=True
            )
            print(f"原日志文件被占用，使用备用日志文件: {alt_log_file}")
        except Exception as e:
            # 如果仍然失败，只使用控制台输出
            print(f"无法创建日志文件处理器: {e}")
            handler = logging.StreamHandler()
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # 添加控制台处理器，确保日志同时输出到控制台
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.addHandler(console)
    logger.setLevel(logging.INFO)
    
    return logger

def run_spider_process(spider_name, project_root, movie_name):
    """在子进程中运行爬虫"""
    logger = setup_logging("spider_process")
    
    try:
        # 设置当前工作目录为爬虫项目目录
        # 原来的路径不正确，修改为正确的路径
        crawler_dir = os.path.join(project_root, 'CollectIp', 'ip_operator', 'crawl_ip', 'crawl_ip')
        logger.info(f"尝试切换到目录: {crawler_dir}")
        
        # 检查目录是否存在
        if not os.path.exists(crawler_dir):
            logger.error(f"目录不存在: {crawler_dir}")
            
            # 尝试查找正确的目录
            alt_dir = os.path.join(project_root, 'CollectIp', 'ip_operator', 'crawl_ip')
            logger.info(f"尝试备用目录: {alt_dir}")
            
            if os.path.exists(alt_dir):
                crawler_dir = alt_dir
                logger.info(f"使用备用目录: {crawler_dir}")
            else:
                raise FileNotFoundError(f"找不到爬虫目录: {crawler_dir} 或 {alt_dir}")
        
        # 切换工作目录
        os.chdir(crawler_dir)
        
        # 检查目录
        logger.info(f"当前工作目录: {os.getcwd()}")
        
        # 导入必要的Spider组件
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.project import get_project_settings
        from importlib import import_module
        
        # 设置电影名环境变量，供爬虫使用
        os.environ['MOVIE_NAME'] = movie_name
        
        # 加载爬虫设置
        settings = get_project_settings()
        settings.set('LOG_LEVEL', 'INFO')
        
        # 创建爬虫进程
        process = CrawlerProcess(settings)
        
        # 动态导入爬虫类
        try:
            # 先尝试直接导入
            spider_module = import_module(f"crawl_ip.spiders.{spider_name}")
            logger.info(f"成功导入模块: crawl_ip.spiders.{spider_name}")
        except ImportError as e:
            logger.warning(f"导入模块失败: {e}，尝试备用导入方式")
            # 备用导入方式
            try:
                spider_module = import_module(f"crawl_ip.crawl_ip.spiders.{spider_name}")
                logger.info(f"成功使用备用方式导入模块: crawl_ip.crawl_ip.spiders.{spider_name}")
            except ImportError:
                # 完整路径尝试
                spider_module = import_module(f"ip_operator.crawl_ip.crawl_ip.crawl_ip.spiders.{spider_name}")
                logger.info(f"成功使用完整路径导入模块: ip_operator.crawl_ip.crawl_ip.crawl_ip.spiders.{spider_name}")
        
        # 找到爬虫类并启动
        spider_class = None
        for obj_name in dir(spider_module):
            obj = getattr(spider_module, obj_name)
            # 检查是否是爬虫类且名称匹配
            if hasattr(obj, 'name') and obj.name == spider_name:
                logger.info(f"启动爬虫: {obj.name}")
                spider_class = obj
                break
        
        if spider_class is None:
            logger.error(f"未找到爬虫类: {spider_name}")
            raise ValueError(f"在模块中未找到名为 {spider_name} 的爬虫类")
                
        # 启动爬虫
        process.crawl(spider_class, movie_name=movie_name)
        
        # 启动爬虫进程
        process.start()  # 这会阻塞直到所有爬虫完成
        
        # 爬虫完成后的处理
        logger.info(f"爬虫 {spider_name} 已完成运行")
        return 0  # 成功退出码
        
    except Exception as e:
        logger.error(f"运行爬虫时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1  # 错误退出码
    
    finally:
        # 清理环境变量
        if 'MOVIE_NAME' in os.environ:
            del os.environ['MOVIE_NAME']

def start_douban_crawl(movie_name):
    """开始豆瓣爬虫"""
    logger = setup_logging("douban_crawler")
    
    # 记录Python路径
    logger.info(f"Python路径: {sys.path}")
    logger.info(f"项目根目录: {PROJECT_ROOT}")
    
    try:
        # 保存原始工作目录
        original_dir = os.getcwd()
        logger.info(f"当前工作目录: {original_dir}")
        
        # 添加项目根目录到Python路径
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
            
        # 设置要爬取的电影名
        os.environ['MOVIE_NAME'] = movie_name
        logger.info(f"设置要爬取的电影: {movie_name}")
        
        # 使用Process创建子进程
        spider_process = Process(
            target=run_spider_process,
            args=('douban', PROJECT_ROOT, movie_name)
        )
        
        # 启动子进程
        logger.info("启动爬虫子进程")
        spider_process.start()
        
        # 等待子进程结束
        spider_process.join()
        
        # 检查子进程退出码
        if spider_process.exitcode != 0:
            logger.error(f"爬虫进程异常退出，退出码: {spider_process.exitcode}")
            return False
            
        logger.info("爬虫进程已完成")
        return True
        
    except Exception as e:
        logger.error(f"启动爬虫失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    finally:
        # 清理环境变量
        if 'MOVIE_NAME' in os.environ:
            del os.environ['MOVIE_NAME']
            
def start_crawl(spider_name='collectip', crawl_type='qq'):
    """开始爬虫，适用于IP爬虫等"""
    logger = setup_logging("ip_crawler")
    
    try:
        # 保存原始工作目录
        original_dir = os.getcwd()
        logger.info(f"当前工作目录: {original_dir}")
        
        # 添加项目根目录到Python路径
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
            
        # 设置类型环境变量
        os.environ['CRAWL_TYPE'] = crawl_type
        logger.info(f"设置要爬取的类型: {crawl_type}")
        
        # 使用Process创建子进程
        spider_process = Process(
            target=run_spider_process,
            args=(spider_name, PROJECT_ROOT, crawl_type)
        )
        
        # 启动子进程
        logger.info(f"启动爬虫子进程: {spider_name}")
        spider_process.start()
        
        # 等待子进程结束
        spider_process.join()
        
        # 检查子进程退出码
        if spider_process.exitcode != 0:
            logger.error(f"爬虫进程异常退出，退出码: {spider_process.exitcode}")
            return False
            
        logger.info("爬虫进程已完成")
        return True
        
    except Exception as e:
        logger.error(f"启动爬虫失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    finally:
        # 清理环境变量
        if 'CRAWL_TYPE' in os.environ:
            del os.environ['CRAWL_TYPE']

if __name__ == '__main__':
    # start_crawl()
    start_douban_crawl('肖申克的救赎')