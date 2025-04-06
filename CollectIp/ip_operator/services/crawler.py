import os
import sys
import logging
import django
import threading
import time
import json
import traceback
import base64
from logging.handlers import RotatingFileHandler
from pathlib import Path
import signal
import datetime

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

# 添加调试标志 - 开发时设为True，生产环境设为False
DEBUG = True

# 设置日志
def setup_logging(name="ip_operator", level=logging.INFO):
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
        # 创建文件处理器
        handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8',
            delay=True
        )
    except Exception as e:
        # 如果创建失败，使用控制台输出
        print(f"无法创建日志文件处理器: {e}")
        handler = logging.StreamHandler()
    
    # 设置日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # 调试模式使用更详细的日志
    if DEBUG:
        logger.setLevel(logging.DEBUG)
        # 添加控制台处理器，方便调试
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)
    else:
        logger.setLevel(level)
    
    return logger

def find_crawler_dir(project_root):
    """查找爬虫目录"""
    possible_dirs = [
        os.path.join(project_root, 'CollectIp', 'ip_operator', 'crawl_ip', 'crawl_ip'),
        os.path.join(project_root, 'ip_operator', 'crawl_ip', 'crawl_ip'),
        os.path.join(project_root, 'CollectIp', 'ip_operator', 'crawl_ip'),
        os.path.join(project_root, 'ip_operator', 'crawl_ip')
    ]
    
    for dir_path in possible_dirs:
        if os.path.exists(dir_path):
            return dir_path
    return None

def find_spider_module(spider_name):
    """查找爬虫模块"""
    from importlib import import_module
    
    module_paths = [
        f"crawl_ip.spiders.{spider_name}",
        f"spiders.{spider_name}"
    ]
    
    for module_path in module_paths:
        try:
            return import_module(module_path)
        except ImportError:
            continue
    return None

def encode_movie_name(movie_name):
    """将电影名编码为base64字符串（确保可以安全地存储在环境变量中）"""
    if not movie_name:
        return ""
    try:
        # 编码为base64
        return base64.b64encode(movie_name.encode('utf-8')).decode('ascii')
    except Exception as e:
        logger = setup_logging("encoder")
        logger.error(f"编码电影名失败: {str(e)}")
        # 返回一个安全的回退值
        return base64.b64encode("unknown_movie".encode('utf-8')).decode('ascii')

def decode_movie_name(encoded_name):
    """从base64解码电影名"""
    if not encoded_name:
        return ""
    try:
        # 从base64解码
        return base64.b64decode(encoded_name).decode('utf-8')
    except Exception as e:
        logger = setup_logging("decoder")
        logger.error(f"解码电影名失败: {str(e)}")
        return "unknown_movie"

def run_scrapy_spider(spider_name, project_root, input_data=None, crawl_config=None):
    """在线程中运行爬虫的实际执行函数"""
    logger = setup_logging("spider_process", logging.DEBUG)
    logger.debug(f"开始执行爬虫 {spider_name}，参数: {input_data}, 配置: {crawl_config}")
    
    try:
        # 查找并切换到爬虫目录
        crawler_dir = find_crawler_dir(project_root)
        if not crawler_dir:
            logger.error("找不到爬虫目录")
            return 1
            
        os.chdir(crawler_dir)
        logger.debug(f"切换工作目录: {os.getcwd()}")
        
        # 导入Scrapy组件
        from scrapy.crawler import CrawlerRunner
        from scrapy.utils.project import get_project_settings
        from twisted.internet import reactor
        import twisted.internet.error
        from scrapy.utils.log import configure_logging
        
        # 配置Scrapy日志
        configure_logging({"LOG_LEVEL": "INFO" if DEBUG else "WARNING"})
        
        # 设置环境变量
        if spider_name == 'douban_spider' and input_data:
            try:
                # 尝试设置原始电影名（可能会失败）
                os.environ['MOVIE_NAME'] = input_data
                logger.debug(f"成功设置原始电影名环境变量: {input_data}")
            except (UnicodeError, ValueError) as e:
                # 捕获编码错误，记录但不中断程序
                logger.warning(f"设置原始MOVIE_NAME环境变量失败: {str(e)}")
            
            try:
                # 必须设置：编码电影名，确保不会有编码问题
                encoded_movie_name = encode_movie_name(input_data)
                os.environ['MOVIE_NAME_ENCODED'] = encoded_movie_name
                logger.debug(f"设置编码电影名环境变量: {input_data} (编码后: {encoded_movie_name})")
            except Exception as e:
                logger.error(f"设置MOVIE_NAME_ENCODED环境变量失败: {str(e)}")
            
            try:
                # 尝试通过英文变量名来存储原文
                os.environ['MOVIE_NAME_ORIGINAL'] = input_data
                logger.debug(f"成功设置MOVIE_NAME_ORIGINAL环境变量: {input_data}")
            except (UnicodeError, ValueError) as e:
                logger.warning(f"设置MOVIE_NAME_ORIGINAL环境变量失败: {str(e)}")
            
            # 设置一个安全的ASCII电影名环境变量，确保至少有一个可用
            try:
                # 生成安全ASCII名称 - 强制转换为拉丁字符
                safe_movie_name = ''.join(c if ord(c) < 128 else '_' for c in input_data)
                if not safe_movie_name or safe_movie_name.strip() == '':
                    safe_movie_name = 'encoded_movie_' + encoded_movie_name[:8]
                
                # 确保至少有一些有效字符
                if len(safe_movie_name) < 3:
                    safe_movie_name = 'movie_' + encoded_movie_name[:8]
                    
                os.environ['MOVIE_NAME_ASCII'] = safe_movie_name
                logger.debug(f"设置安全ASCII电影名环境变量: {safe_movie_name}")
            except Exception as e:
                # 如果连ASCII处理也失败，使用固定字符串
                try:
                    os.environ['MOVIE_NAME_ASCII'] = 'movie_fallback'
                    logger.error(f"使用备用电影名: movie_fallback，原因: {str(e)}")
                except Exception as ex:
                    logger.critical(f"设置所有电影名环境变量均失败: {str(ex)}")
                
        elif spider_name == 'collectip' and input_data:
            os.environ['CRAWL_TYPE'] = input_data
            logger.debug(f"设置爬取类型环境变量: {input_data}")
        
        # 设置爬取配置
        if crawl_config:
            try:
                os.environ['CRAWL_CONFIG'] = json.dumps(crawl_config)
                logger.debug(f"设置爬取配置环境变量: {json.dumps(crawl_config)}")
            except Exception as e:
                logger.error(f"序列化配置失败: {str(e)}")
        
        # 加载爬虫设置并禁用信号处理
        settings = get_project_settings()
        settings.set('LOG_LEVEL', 'INFO' if DEBUG else 'WARNING')
        settings.set('ROBOTSTXT_OBEY', False)
        # 禁用信号处理以防止非主线程错误
        settings.set('EXTENSIONS', {
            'scrapy.extensions.telnet.TelnetConsole': None,
            'scrapy.extensions.corestats.CoreStats': None,
            'scrapy.extensions.memusage.MemoryUsage': None,
            'scrapy.extensions.logstats.LogStats': None,
        })
        logger.debug("已加载爬虫设置")
        
        # 导入爬虫模块并查找爬虫类
        spider_module = find_spider_module(spider_name)
        if not spider_module:
            logger.error(f"无法导入爬虫模块: {spider_name}")
            return 1
        
        logger.debug(f"成功导入爬虫模块: {spider_module.__name__}")
        
        # 查找爬虫类
        spider_class = None
        for obj_name in dir(spider_module):
            obj = getattr(spider_module, obj_name)
            if hasattr(obj, 'name') and getattr(obj, 'name') == spider_name:
                spider_class = obj
                break
        
        if not spider_class:
            logger.error(f"未找到爬虫类: {spider_name}")
            return 1
                
        logger.debug(f"找到爬虫类: {spider_class.__name__}")
        
        # 准备爬虫参数
        spider_kwargs = {}
        
        # 处理配置参数
        if crawl_config:
            if spider_name == 'douban_spider':
                if 'strategy' in crawl_config:
                    spider_kwargs['comment_strategy'] = crawl_config['strategy']
                    
                    for param in ['max_pages', 'sample_size', 'max_interval', 'block_size', 'use_random_strategy']:
                        if param in crawl_config:
                            spider_kwargs[param] = crawl_config[param]
            elif spider_name == 'collectip' and 'crawl_type' in crawl_config:
                spider_kwargs['crawl_type'] = crawl_config['crawl_type']
                    
            logger.debug(f"爬虫参数: {spider_kwargs}")
        
        # 使用CrawlerRunner运行爬虫
        runner = CrawlerRunner(settings)
        logger.debug("创建CrawlerRunner实例")
        
        # 创建完成事件
        finished = threading.Event()
        
        # 定义爬虫完成后的回调
        def on_spider_closed(spider):
            logger.debug(f"爬虫 {spider.name} 已完成")
            finished.set()
        
        # 添加爬虫完成的回调
        crawler = runner.create_crawler(spider_class)
        crawler.signals.connect(on_spider_closed, signal='spider_closed')
        
        # 启动爬虫
        logger.debug("开始运行爬虫")
        deferred = crawler.crawl(**spider_kwargs)
        
        # 启动reactor
        if not reactor.running:
            # 在新线程中运行reactor
            reactor_thread = threading.Thread(target=reactor.run, 
                                             kwargs={'installSignalHandlers': False})
            reactor_thread.daemon = True
            reactor_thread.start()
            logger.debug("Reactor已在子线程中启动")
        
        # 等待爬虫完成
        logger.debug("等待爬虫完成...")
        finished.wait(timeout=3600)  # 最多等待1小时
        
        if finished.is_set():
            logger.debug("爬虫已正常完成")
        else:
            logger.warning("爬虫超时或未正常完成")
        
        return 0  # 成功
        
    except Exception as e:
        logger.error(f"运行爬虫时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return 1  # 失败
    
    finally:
        # 清理环境变量，注意先检查是否存在
        for var in ['MOVIE_NAME', 'MOVIE_NAME_ENCODED', 'MOVIE_NAME_ORIGINAL', 'MOVIE_NAME_ASCII', 'CRAWL_CONFIG', 'CRAWL_TYPE']:
            if var in os.environ:
                try:
                    del os.environ[var]
                    logger.debug(f"成功清理环境变量: {var}")
                except Exception as e:
                    logger.error(f"清理环境变量 {var} 失败: {str(e)}")
        logger.debug("清理环境变量完成")


def start_douban_crawl(movie_name, crawl_config=None):
    """开始豆瓣爬虫"""
    logger = setup_logging("douban_crawler", logging.DEBUG)
    logger.debug(f"准备启动豆瓣爬虫: {movie_name}")

    try:
        # 记录爬取信息
        strategy = crawl_config.get('strategy', 'sequential') if crawl_config else 'sequential'
        logger.debug(f"爬取策略: {strategy}, 配置: {crawl_config}")

        # 创建并启动爬虫线程
        spider_thread = threading.Thread(
            target=run_scrapy_spider,
            args=('douban_spider', str(PROJECT_ROOT), movie_name, crawl_config),
            name=f"DoubanSpider-{int(time.time())}"
        )
        # 设置为非守护线程，确保主程序退出前线程能完成
        spider_thread.daemon = False
        spider_thread.start()
        
        logger.debug(f"爬虫线程已启动: {spider_thread.name}")
        return True
    except Exception as e:
        logger.error(f"启动爬虫时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def start_douban_crawl_with_params(movie_name, strategy="sequential", max_pages=None, sample_size=None, 
                      max_interval=None, block_size=None, use_random_strategy=None):
    """启动豆瓣爬虫线程，支持所有参数"""
    logger = setup_logging("douban_crawler", logging.DEBUG)
    logger.debug(f"使用参数启动豆瓣爬虫: {movie_name}, 策略: {strategy}")
    
    try:
        # 构建爬取配置
        crawl_config = {'strategy': strategy}
        
        # 添加可选参数
        params = {
            'max_pages': max_pages,
            'sample_size': sample_size,
            'max_interval': max_interval,
            'block_size': block_size,
            'use_random_strategy': use_random_strategy
        }
        
        # 过滤掉None值
        crawl_config.update({k: v for k, v in params.items() if v is not None})
        logger.debug(f"最终配置参数: {crawl_config}")
            
        # 启动爬虫
        return start_douban_crawl(movie_name, crawl_config)
    except Exception as e:
        logger.error(f"启动爬虫出错: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def generate_lock_file_path(spider_name):
    """生成爬虫锁文件路径"""
    # 确保锁文件目录存在
    lock_dir = os.path.join(PROJECT_ROOT, 'locks')
    os.makedirs(lock_dir, exist_ok=True)
    
    # 返回锁文件路径
    return os.path.join(lock_dir, f'crawler_{spider_name}.lock')


def start_crawl(spider_name='collectip', crawl_type='qq'):
    """开始爬虫，适用于IP爬虫等"""
    logger = setup_logging("ip_crawler", logging.DEBUG)
    logger.debug(f"准备启动IP爬虫: {spider_name}, 类型: {crawl_type}")
    
    # 爬虫锁文件路径
    lock_file = generate_lock_file_path(spider_name)
    logger.debug(f"锁文件路径: {lock_file}")
    
    # 检查锁文件
    if os.path.exists(lock_file):
        # 检查锁文件是否过期（超过1小时）
        if os.path.getmtime(lock_file) < (time.time() - 3600):
            logger.debug(f"爬虫锁文件已过期，删除锁文件")
            os.remove(lock_file)
        else:
            logger.warning(f"爬虫正在运行中，跳过本次任务: {spider_name}")
            return False
    
    # 创建锁文件 - 此步骤提前，但不在finally中删除
    try:
        with open(lock_file, 'w', encoding='utf-8') as f:
            f.write(f"{os.getpid()},{time.time()}")
        logger.debug(f"创建锁文件: {lock_file}")
            
        # 配置爬虫参数
        logger.debug(f"开始爬取IP，类型: {crawl_type}")
        crawl_config = {'crawl_type': crawl_type}
        
        # 创建并启动爬虫线程
        spider_thread = threading.Thread(
            target=run_scrapy_spider,
            args=(spider_name, PROJECT_ROOT, crawl_type, crawl_config),
            name=f"IpSpider-{crawl_type}-{int(time.time())}"
        )
        # 设置为非守护线程，确保主程序退出前线程能完成
        spider_thread.daemon = False
        spider_thread.start()
        
        logger.debug(f"爬虫线程已启动: {spider_thread.name}")
        return True
    except Exception as e:
        logger.error(f"启动爬虫时出错: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 发生异常时删除锁文件
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
                logger.debug("删除锁文件成功")
            except Exception as ex:
                logger.error(f"删除爬虫锁文件时出错: {ex}")
        return False


# 当作为脚本直接运行时的入口点
if __name__ == '__main__':
    # 设置Django环境
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CollectIp.settings')
    django.setup()
    
    # 测试爬虫
    print("开始测试爬虫...")
    result = start_douban_crawl_with_params('霸王别姬', strategy='sequential', max_pages=2)
    print(f"爬虫启动结果: {result}")
    
    # 防止主程序退出导致线程终止
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("手动终止程序")