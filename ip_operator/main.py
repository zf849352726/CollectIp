import os
import sys
import time
import logging
from db_operations import DatabaseOperator
from ip_scorer import IPScorer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 添加爬虫项目路径（修改这部分）
CRAWLER_ROOT = os.path.dirname(os.path.abspath(__file__))
CRAWLER_PATH = os.path.join(CRAWLER_ROOT, 'crawl_ip', 'crawl_ip', 'crawl_ip')  # 修改路径
sys.path.insert(0, CRAWLER_PATH)  # 添加爬虫根目录到路径

def run_spider():
    """运行爬虫收集IP"""
    try:
        # 设置爬虫项目路径
        CRAWLER_ROOT = os.path.dirname(os.path.abspath(__file__))
        PROJECT_ROOT = os.path.join(CRAWLER_ROOT, 'crawl_ip', 'crawl_ip', 'crawl_ip')
        
        # 添加父目录到 Python 路径
        PARENT_DIR = os.path.dirname(PROJECT_ROOT)
        if PARENT_DIR not in sys.path:
            sys.path.insert(0, PARENT_DIR)
        
        # 设置工作目录
        original_dir = os.getcwd()
        os.chdir(PROJECT_ROOT)
        
        # 设置 Scrapy 设置模块
        os.environ['SCRAPY_SETTINGS_MODULE'] = 'crawl_ip.settings'
        
        logging.info(f"Python路径: {sys.path}")
        logging.info(f"当前工作目录: {os.getcwd()}")
        logging.info(f"设置模块: {os.environ['SCRAPY_SETTINGS_MODULE']}")
        
        # 导入和运行爬虫
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.project import get_project_settings
        from crawl_ip.spiders.collectip import CollectipSpider  # 使用完整的导入路径
        
        # 获取爬虫设置并创建进程
        settings = get_project_settings()
        process = CrawlerProcess(settings)
        
        # 运行爬虫
        process.crawl(CollectipSpider)
        process.start(stop_after_crawl=True)
        
        logging.info("爬虫任务执行完成")
        return True
    except Exception as e:
        logging.error(f"爬虫任务执行失败: {e}")
        return False
    finally:
        # 恢复原始工作目录
        os.chdir(original_dir)

def main():
    db = DatabaseOperator()
    scorer = IPScorer()
    
    # 初始化最后爬取时间
    last_crawl_time = 0
    
    while True:
        try:
            # 获取IP池数据
            logging.info("开始获取IP池数据...")
            ip_pool = db.get_ip_pool()
            
            # 检查是否需要执行爬虫任务
            current_time = time.time()
            if not ip_pool or (current_time - last_crawl_time >= 3600):  # 1小时间隔
                logging.warning("IP池为空或达到爬虫间隔时间，开始执行爬虫任务...")
                
                spider_success = run_spider()
                if spider_success:
                    last_crawl_time = current_time
                
                # 如果IP池为空且爬虫执行失败，等待后重试
                if not ip_pool:
                    time.sleep(300)  # 等待5分钟
                    continue
                
                # 重新获取IP池数据
                ip_pool = db.get_ip_pool()
            
            if not ip_pool:
                logging.warning("IP池仍然为空，等待下一轮检查...")
                time.sleep(300)
                continue
                
            # 提取IP地址列表
            ip_list = [item['server'] for item in ip_pool]
            
            # 进行IP打分
            logging.info(f"开始对 {len(ip_list)} 个IP进行打分...")
            scores = scorer.score_ip_pool(ip_list)
            
            # 更新分数到数据库（低于10分的IP会被删除）
            for server, score in scores.items():
                logging.info(f"IP: {server}, 得分: {score}")
                db.update_ip_score(server, score)
            
            logging.info("本轮打分完成")
            time.sleep(3600)  # 1小时后进行下一轮打分
            
        except Exception as e:
            logging.error(f"发生错误: {e}")
            time.sleep(300)  # 发生错误后等待5分钟再重试


if __name__ == "__main__":
    main()
