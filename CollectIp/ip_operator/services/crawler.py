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
import base64

# 设置Django环境
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 添加项目根目录到Python路径
sys.path.insert(0, BASE_DIR)
# 添加Django项目目录到Python路径
DJANGO_PROJECT_DIR = os.path.join(BASE_DIR, 'CollectIp')
sys.path.insert(0, DJANGO_PROJECT_DIR)

# 只有在单独运行这个脚本时才打印详细日志信息
if __name__ == '__main__':
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"DJANGO_PROJECT_DIR: {DJANGO_PROJECT_DIR}")
    print(f"Python Path: {sys.path}")
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
def setup_logging(name="ip_operator", level=logging.WARNING):
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
    
    # 使用简化的日志格式，只包含时间、级别和消息
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # 只在DEBUG模式下添加控制台处理器
    if level == logging.DEBUG:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)
    
    logger.addHandler(handler)
    logger.setLevel(level)
    
    return logger

# 处理中文编码的函数
def encode_movie_name(movie_name):
    """使用Base64编码电影名，解决中文编码问题"""
    try:
        encoded_name = base64.b64encode(movie_name.encode('utf-8')).decode('ascii')
        return encoded_name
    except Exception as e:
        print(f"编码电影名称出错: {str(e)}")
        return None
        
def decode_movie_name(encoded_name):
    """解码Base64编码的电影名"""
    try:
        decoded_name = base64.b64decode(encoded_name.encode('ascii')).decode('utf-8')
        return decoded_name
    except Exception as e:
        print(f"解码电影名称出错: {str(e)}")
        return None

def run_spider_process(spider_name, project_root, movie_name, crawl_config=None):
    """在子进程中运行爬虫"""
    logger = setup_logging("spider_process", logging.WARNING)
    
    try:
        # 设置当前工作目录为爬虫项目目录
        # 可能的爬虫目录列表
        possible_dirs = [
            os.path.join(project_root, 'CollectIp', 'ip_operator', 'crawl_ip', 'crawl_ip'),
            os.path.join(project_root, 'CollectIp', 'ip_operator', 'crawl_ip')
        ]
        
        # 查找第一个存在的目录
        crawler_dir = None
        for dir_path in possible_dirs:
            if os.path.exists(dir_path):
                crawler_dir = dir_path
                break
                
        if crawler_dir is None:
            logger.error("找不到爬虫目录")
            return 1
            
        # 切换工作目录
        os.chdir(crawler_dir)
        logger.warning(f"当前工作目录: {os.getcwd()}")
        
        # 导入必要的Spider组件
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.project import get_project_settings
        from importlib import import_module
        
        # 使用Base64编码电影名
        try:
            encoded_movie_name = encode_movie_name(movie_name)
            if encoded_movie_name:
                os.environ['MOVIE_NAME_ENCODED'] = encoded_movie_name
                logger.warning(f"电影名已Base64编码: {movie_name} -> {encoded_movie_name}")
        except Exception as e:
            logger.error(f"编码电影名出错: {str(e)}")
            
        # 同时设置原始电影名作为备份
        os.environ['MOVIE_NAME'] = movie_name
        
        # 将爬取配置设置为环境变量
        if crawl_config:
            import json
            os.environ['CRAWL_CONFIG'] = json.dumps(crawl_config)
            logger.warning(f"设置爬取配置: {crawl_config}")
        
        # 加载爬虫设置
        settings = get_project_settings()
        settings.set('LOG_LEVEL', 'WARNING')  # 提高日志级别，减少输出
        settings.set('ROBOTSTXT_OBEY', False)  # 忽略robots.txt
        
        # 创建爬虫进程
        process = CrawlerProcess(settings)
        
        # 可能的模块导入路径
        module_paths = [
            f"crawl_ip.spiders.{spider_name}",
            f"crawl_ip.crawl_ip.spiders.{spider_name}",
            f"ip_operator.crawl_ip.crawl_ip.crawl_ip.spiders.{spider_name}"
        ]
        
        # 尝试导入爬虫模块
        spider_module = None
        for module_path in module_paths:
            try:
                spider_module = import_module(module_path)
                logger.warning(f"成功导入爬虫模块: {module_path}")
                break
            except ImportError as e:
                logger.warning(f"尝试导入 {module_path} 失败: {str(e)}")
                continue
                
        if spider_module is None:
            logger.error(f"无法导入爬虫模块: {spider_name}")
            return 1
        
        # 找到爬虫类并启动
        spider_class = None
        for obj_name in dir(spider_module):
            obj = getattr(spider_module, obj_name)
            # 检查是否是爬虫类且名称匹配
            if hasattr(obj, 'name') and obj.name == spider_name:
                spider_class = obj
                break
        
        if spider_class is None:
            logger.error(f"未找到爬虫类: {spider_name}")
            return 1
                
        # 准备爬虫参数
        spider_kwargs = {}
        
        # 如果有配置参数，添加到爬虫参数中
        if crawl_config:
            # 添加策略参数
            if 'strategy' in crawl_config:
                spider_kwargs['comment_strategy'] = crawl_config['strategy']
                
                # 添加各种策略特定的参数
                for param in ['max_pages', 'sample_size', 'max_interval', 'block_size', 'use_random_strategy']:
                    if param in crawl_config:
                        spider_kwargs[param] = crawl_config[param]
                        
            logger.warning(f"启动爬虫，参数: {spider_kwargs}")
        
        # 启动爬虫
        process.crawl(spider_class, **spider_kwargs)
        process.start()  # 这会阻塞直到所有爬虫完成
        
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
        if 'MOVIE_NAME_ENCODED' in os.environ:
            del os.environ['MOVIE_NAME_ENCODED']
        if 'CRAWL_CONFIG' in os.environ:
            del os.environ['CRAWL_CONFIG']

def start_douban_crawl(movie_name, crawl_config=None):
    """开始豆瓣爬虫"""
    logger = setup_logging("douban_crawler", logging.WARNING)
    
    try:
        # 添加项目根目录到Python路径
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
            
        # 设置要爬取的电影名
        os.environ['MOVIE_NAME'] = movie_name
        
        # 记录策略配置
        if crawl_config:
            strategy = crawl_config.get('strategy', 'sequential')
            logger.warning(f"开始爬取电影: {movie_name}，使用策略: {strategy}")
        else:
            logger.warning(f"开始爬取电影: {movie_name}，使用默认策略")
        
        # 使用Process创建子进程
        spider_process = Process(
            target=run_spider_process,
            args=('douban_spider', str(PROJECT_ROOT), movie_name, crawl_config)
        )
        
        # 启动子进程
        spider_process.start()
        logger.warning(f"爬虫进程已启动，PID: {spider_process.pid}")
        
        # 等待子进程完成
        spider_process.join()
        
        # 检查子进程的退出码
        if spider_process.exitcode == 0:
            logger.warning("爬虫任务完成")
            return True
        else:
            logger.error(f"爬虫任务失败，退出码: {spider_process.exitcode}")
            return False
            
    except Exception as e:
        logger.error(f"启动爬虫时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def start_douban_crawl_with_params(movie_name, strategy="sequential", max_pages=None, sample_size=None, 
                      max_interval=None, block_size=None, use_random_strategy=None):
    """启动豆瓣爬虫进程，支持所有参数"""
    logger = setup_logging("douban_crawler", logging.WARNING)

    try:
        # 构建爬取配置
        crawl_config = {
            'strategy': strategy
        }
        
        # 添加各种可选参数
        if max_pages is not None:
            crawl_config['max_pages'] = max_pages
        if sample_size is not None:
            crawl_config['sample_size'] = sample_size
        if max_interval is not None:
            crawl_config['max_interval'] = max_interval  
        if block_size is not None:
            crawl_config['block_size'] = block_size
        if use_random_strategy is not None:
            crawl_config['use_random_strategy'] = use_random_strategy
            
        # 调用主函数启动爬虫
        logger.warning(f"准备爬取电影: {movie_name}，使用策略: {strategy}，参数: {crawl_config}")
        return start_douban_crawl(movie_name, crawl_config)
        
    except Exception as e:
        logger.error(f"启动爬虫出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def start_crawl(spider_name='collectip', crawl_type='qq'):
    """开始爬虫，适用于IP爬虫等"""
    logger = setup_logging("ip_crawler", logging.WARNING)
    
    # 爬虫锁文件路径
    lock_file = os.path.join(PROJECT_ROOT, f'crawler_{spider_name}.lock')
    
    # 检查锁文件
    if os.path.exists(lock_file):
        # 检查锁文件是否过期（超过1小时）
        if os.path.getmtime(lock_file) < (time.time() - 3600):
            logger.warning(f"爬虫锁文件已过期，删除锁文件: {lock_file}")
            os.remove(lock_file)
        else:
            logger.warning(f"爬虫正在运行中，跳过本次任务: {spider_name}")
            return False
    
    try:
        # 创建锁文件
        with open(lock_file, 'w') as f:
            f.write(f"{os.getpid()},{time.time()}")
            
        # 添加项目根目录到Python路径
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
            
        # 设置类型环境变量
        os.environ['CRAWL_TYPE'] = crawl_type
        logger.warning(f"开始爬取IP，类型: {crawl_type}")
        
        # 使用Process创建子进程
        spider_process = Process(
            target=run_spider_process,
            args=(spider_name, PROJECT_ROOT, crawl_type)
        )
        
        # 启动子进程
        spider_process.start()
        logger.warning(f"爬虫进程已启动，PID: {spider_process.pid}")
        
        # 等待子进程完成
        spider_process.join(timeout=3600)  # 最多等待1小时
        
        # 检查进程是否还在运行
        if spider_process.is_alive():
            logger.error(f"爬虫进程超时，强制终止: {spider_process.pid}")
            spider_process.terminate()
            time.sleep(5)  # 等待进程终止
            if spider_process.is_alive():
                logger.error("无法终止爬虫进程，尝试更强力的终止")
                import signal
                os.kill(spider_process.pid, signal.SIGKILL)
            return False
            
        # 检查退出码
        if spider_process.exitcode == 0:
            logger.warning("爬虫任务完成")
            return True
        else:
            logger.error(f"爬虫任务失败，退出码: {spider_process.exitcode}")
            return False
            
    except Exception as e:
        logger.error(f"启动爬虫时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        # 清理环境变量
        if 'CRAWL_TYPE' in os.environ:
            del os.environ['CRAWL_TYPE']
            
        # 清理锁文件
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except Exception as e:
                logger.error(f"删除爬虫锁文件时出错: {e}")

if __name__ == '__main__':
    start_crawl()
    # start_douban_crawl('出走的决心')
