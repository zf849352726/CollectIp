from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import os
import sys
import logging
import django
from multiprocessing import Process

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

logger = logging.getLogger(__name__)

def run_spider_process(spider_name, project_root, movie_name):
    """在单独进程中运行爬虫"""
    try:
        # 切换到爬虫项目目录
        os.chdir(project_root)
        
        # 导入和设置Scrapy
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.project import get_project_settings
        
        # 获取爬虫类
        if spider_name == 'douban':
            from crawl_ip.spiders.douban_spider import DoubanSpider
            spider_class = DoubanSpider
        else:
            from crawl_ip.spiders.collectip import CollectipSpider
            spider_class = CollectipSpider
        
        # 运行爬虫
        settings = get_project_settings()
        process = CrawlerProcess(settings)
        process.crawl(spider_class, movie_names=movie_name)
        process.start()
        
    except Exception as e:
        print(f"爬虫运行错误: {str(e)}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)

def start_crawl():
    """
    启动IP采集任务
    """
    try:
        logger.info("开始执行IP采集任务")
        
        # 设置爬虫项目路径
        CRAWLER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        PROJECT_ROOT = os.path.join(CRAWLER_ROOT, 'crawl_ip', 'crawl_ip')
        
        # 添加路径到 Python 路径
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
            
        # 保存原始工作目录
        original_dir = os.getcwd()
        
        try:
            # 检查爬虫项目目录是否存在
            if not os.path.exists(PROJECT_ROOT):
                logger.error(f"爬虫项目目录不存在: {PROJECT_ROOT}")
                raise FileNotFoundError(f"爬虫项目目录不存在: {PROJECT_ROOT}")
                
            # 记录调试信息
            logger.info(f"Python路径: {sys.path}")
            logger.info(f"爬虫项目目录: {PROJECT_ROOT}")
            logger.info(f"当前工作目录: {os.getcwd()}")
            
            # 创建并启动子进程
            spider_process = Process(
                target=run_spider_process,
                args=('settings', PROJECT_ROOT)
            )
            spider_process.start()
            
            # 等待爬虫完成
            logger.info("爬虫进程已启动，等待完成...")
            spider_process.join()
            
            if spider_process.exitcode == 0:
                logger.info("IP采集任务执行完成")
                return True
            else:
                logger.error(f"IP采集进程异常退出，退出代码: {spider_process.exitcode}")
                return False
                
        finally:
            # 恢复原始工作目录
            os.chdir(original_dir)
            
    except Exception as e:
        logger.error(f"IP采集任务执行失败: {str(e)}")
        logger.exception("详细错误信息：")
        return False

def start_douban_crawl(movie_name):
    """
    启动豆瓣爬虫进程
    Args:
        movie_name: 要爬取的电影名称
    Returns:
        bool: 爬虫是否成功执行
    """
    try:
        # 设置爬虫项目路径
        CRAWLER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        PROJECT_ROOT = os.path.join(CRAWLER_ROOT, 'crawl_ip', 'crawl_ip')
        
        # 添加路径到 Python 路径
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
            
        # 保存原始工作目录
        original_dir = os.getcwd()
        
        try:
            # 检查爬虫项目目录是否存在
            if not os.path.exists(PROJECT_ROOT):
                logger.error(f"爬虫项目目录不存在: {PROJECT_ROOT}")
                raise FileNotFoundError(f"爬虫项目目录不存在: {PROJECT_ROOT}")
                
            # 记录调试信息
            logger.info(f"Python路径: {sys.path}")
            logger.info(f"爬虫项目目录: {PROJECT_ROOT}")
            logger.info(f"当前工作目录: {os.getcwd()}")
            
            # 创建并启动子进程
            spider_process = Process(
                target=run_spider_process,
                args=('douban', PROJECT_ROOT, movie_name)
            )
            spider_process.start()
            
            # 等待爬虫完成
            logger.info("豆瓣爬虫进程已启动，等待完成...")
            spider_process.join()
            
            if spider_process.exitcode == 0:
                logger.info("豆瓣电影采集任务执行完成")
                return True
            else:
                logger.error(f"豆瓣电影采集进程异常退出，退出代码: {spider_process.exitcode}")
                return False
                
        finally:
            # 恢复原始工作目录
            os.chdir(original_dir)
            
    except Exception as e:
        logger.error(f"豆瓣电影采集任务执行失败: {str(e)}")
        logger.exception("详细错误信息：")
        return False

if __name__ == '__main__':
    # start_crawl()
    start_douban_crawl('肖申克的救赎')