#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试爬虫模块功能的脚本
"""

import os
import sys
import time
import logging
import argparse

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '../..'))
sys.path.insert(0, project_root)

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CollectIp.settings')

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(project_root, 'logs', 'test_crawler.log'))
    ]
)
logger = logging.getLogger(__name__)

def test_douban_crawler(movie_name, strategy="sequential", max_pages=5):
    """测试豆瓣爬虫的功能"""
    try:
        import django
        django.setup()
        
        from ip_operator.services.crawler import start_douban_crawl_with_params, encode_movie_name
        
        # 检查编码处理
        encoded_name = encode_movie_name(movie_name)
        if encoded_name:
            logger.info(f"电影名称 '{movie_name}' 已成功编码为: {encoded_name}")
        else:
            logger.error(f"无法编码电影名称: {movie_name}")
            return False
        
        # 启动爬虫
        logger.info(f"开始测试爬虫: 电影={movie_name}, 策略={strategy}, 页数={max_pages}")
        result = start_douban_crawl_with_params(
            movie_name=movie_name,
            strategy=strategy,
            max_pages=max_pages
        )
        
        # 检查结果
        if result:
            logger.info("爬虫启动成功! 后台进程正在运行")
            return True
        else:
            logger.error("爬虫启动失败")
            return False
            
    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        logger.error("请确保已激活正确的虚拟环境")
        return False
    except Exception as e:
        logger.error(f"测试爬虫时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_ip_crawler():
    """测试IP爬虫的功能"""
    try:
        import django
        django.setup()
        
        from ip_operator.services.crawler import start_crawl
        
        # 启动爬虫
        logger.info("开始测试IP爬虫")
        result = start_crawl(spider_name='collectip', crawl_type='qq')
        
        # 检查结果
        if result:
            logger.info("IP爬虫启动成功! 后台进程正在运行")
            return True
        else:
            logger.error("IP爬虫启动失败")
            return False
            
    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        logger.error("请确保已激活正确的虚拟环境")
        return False
    except Exception as e:
        logger.error(f"测试爬虫时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_crawler_logs():
    """检查爬虫日志文件"""
    logs_dir = os.path.join(project_root, 'logs')
    if not os.path.exists(logs_dir):
        logger.error(f"日志目录不存在: {logs_dir}")
        return
        
    log_files = [
        'douban_crawler.log',
        'spider_process.log',
        'ip_crawler.log'
    ]
    
    for log_file in log_files:
        log_path = os.path.join(logs_dir, log_file)
        if os.path.exists(log_path):
            logger.info(f"日志文件 {log_file} 存在")
            
            # 获取文件大小和修改时间
            size = os.path.getsize(log_path)
            mtime = os.path.getmtime(log_path)
            mtime_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
            
            logger.info(f"  大小: {size / 1024:.2f} KB")
            logger.info(f"  修改时间: {mtime_str}")
            
            # 输出最后10行内容
            logger.info(f"  最后10行内容:")
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-10:]:
                        logger.info(f"    {line.strip()}")
            except UnicodeDecodeError:
                logger.warning(f"  无法以UTF-8编码读取文件，尝试使用latin-1")
                try:
                    with open(log_path, 'r', encoding='latin-1') as f:
                        lines = f.readlines()
                        for line in lines[-10:]:
                            logger.info(f"    {line.strip()}")
                except Exception as e:
                    logger.error(f"  读取日志文件失败: {e}")
            except Exception as e:
                logger.error(f"  读取日志文件失败: {e}")
        else:
            logger.warning(f"日志文件 {log_file} 不存在")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试爬虫模块功能")
    parser.add_argument('--type', '-t', choices=['douban', 'ip', 'logs'], default='douban',
                       help="测试类型: douban=豆瓣爬虫, ip=IP爬虫, logs=检查日志")
    parser.add_argument('--movie', '-m', default='霸王别姬',
                       help="要爬取的电影名称")
    parser.add_argument('--strategy', '-s', default='sequential',
                       choices=['sequential', 'random_pages', 'random_interval', 'random_block', 'random'],
                       help="爬取策略")
    parser.add_argument('--pages', '-p', type=int, default=5,
                       help="爬取页数")
    
    args = parser.parse_args()
    
    if args.type == 'douban':
        logger.info("=== 开始测试豆瓣爬虫 ===")
        test_douban_crawler(args.movie, args.strategy, args.pages)
    elif args.type == 'ip':
        logger.info("=== 开始测试IP爬虫 ===")
        test_ip_crawler()
    elif args.type == 'logs':
        logger.info("=== 检查爬虫日志 ===")
        check_crawler_logs()
    
    logger.info("测试完成")

if __name__ == "__main__":
    main() 