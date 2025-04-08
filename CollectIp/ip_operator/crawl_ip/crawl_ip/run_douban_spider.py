#!/usr/bin/env python
"""
直接运行豆瓣爬虫脚本
不依赖Scrapy的模块加载机制，直接实例化爬虫类
"""

import os
import sys
import time
import logging
import json
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 获取当前脚本所在目录
CURRENT_DIR = Path(__file__).resolve().parent
# 将爬虫目录添加到系统路径
sys.path.insert(0, str(CURRENT_DIR))

def run_douban_spider():
    """运行豆瓣爬虫"""
    try:
        # 导入爬虫模块
        from CollectIp.ip_operator.crawl_ip.crawl_ip.crawl_ip.spiders.douban_spider import DoubanSpider
        
        # 设置电影名称和爬取参数
        movie_name = "霸王别姬"
        strategy = "sequential"
        max_pages = 2
        
        logger.info(f"电影名: {movie_name}")
        logger.info(f"策略: {strategy}")
        logger.info(f"最大页数: {max_pages}")
        
        # 设置环境变量
        os.environ['MOVIE_NAME'] = movie_name
        os.environ['MOVIE_NAME_ENCODED'] = movie_name
        
        # 创建爬取配置
        crawl_config = {
            'strategy': strategy,
            'max_pages': max_pages
        }
        
        # 序列化并设置环境变量
        os.environ['CRAWL_CONFIG'] = json.dumps(crawl_config)
        
        # 实例化爬虫
        spider = DoubanSpider(movie_names=movie_name, comment_strategy=strategy)
        
        # 启动爬虫
        logger.info("开始运行爬虫")
        
        # 调用爬虫的start_requests方法
        for request in spider.start_requests():
            logger.info(f"生成请求: {request.url}")
            # 在实际场景下，这里会由Scrapy引擎处理
            
        # 保持脚本运行，让Selenium有足够时间执行
        logger.info("爬虫启动，等待30秒以便浏览器执行...")
        time.sleep(30)
        
        # 清理资源
        if spider.driver is not None:
            logger.info("关闭浏览器")
            spider.driver.quit()
            
        logger.info("爬虫执行完成")
        return True
        
    except Exception as e:
        logger.error(f"运行爬虫出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    run_douban_spider() 