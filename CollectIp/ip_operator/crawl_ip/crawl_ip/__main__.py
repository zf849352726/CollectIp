#!/usr/bin/env python
"""
豆瓣爬虫主模块 - 用于直接从命令行启动爬虫
"""

import os
import sys
import logging
import argparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数，解析参数并启动爬虫"""
    parser = argparse.ArgumentParser(description='启动豆瓣爬虫')
    parser.add_argument('--movie', type=str, help='要爬取的电影名称', default='霸王别姬')
    parser.add_argument('--strategy', type=str, help='爬取策略', default='sequential')
    parser.add_argument('--max-pages', type=int, help='最大爬取页数', default=2)
    args = parser.parse_args()
    
    # 打印参数
    logger.info(f"电影名: {args.movie}")
    logger.info(f"策略: {args.strategy}")
    logger.info(f"最大页数: {args.max_pages}")
    
    # 设置环境变量
    os.environ['MOVIE_NAME'] = args.movie
    os.environ['MOVIE_NAME_ENCODED'] = args.movie
    
    # 创建爬取配置
    crawl_config = {
        'strategy': args.strategy,
        'max_pages': args.max_pages
    }
    
    # 序列化并设置环境变量
    import json
    os.environ['CRAWL_CONFIG'] = json.dumps(crawl_config)
    
    # 获取项目设置
    settings = get_project_settings()
    
    # 设置项目设置
    settings.set('LOG_LEVEL', 'INFO')
    settings.set('LOG_FORMAT', '%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    settings.set('LOG_STDOUT', True)
    
    # 创建爬虫进程
    process = CrawlerProcess(settings)
    
    # 添加爬虫
    process.crawl('douban_spider')
    
    # 启动爬虫进程
    logger.info("开始运行爬虫")
    process.start()
    logger.info("爬虫结束")

if __name__ == '__main__':
    main() 