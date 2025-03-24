#!/usr/bin/env python
"""
Chrome进程监控和清理脚本
特别针对WebDriver启动的Chrome进程进行监控和清理
"""

import os
import sys
import logging
import signal
import time
import argparse
import platform
from datetime import datetime, timedelta
from pathlib import Path

# 设置路径
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / 'chrome_monitor.log'

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger('chrome_monitor')

# 尝试导入psutil
try:
    import psutil
except ImportError:
    logger.error("请先安装psutil库: pip install psutil")
    sys.exit(1)

def is_webdriver_chrome(proc):
    """检查进程是否是WebDriver启动的Chrome"""
    try:
        # 获取命令行
        cmdline = ' '.join(proc.cmdline()).lower()
        
        # WebDriver特征
        webdriver_markers = [
            'chromedriver',
            '--remote-debugging-port',
            'automation',
            '--test-type',
            'webdriver',
            '--headless'
        ]
        
        # 检查是否符合特征
        for marker in webdriver_markers:
            if marker in cmdline:
                return True
                
        return False
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        return False

def get_process_age(proc):
    """获取进程的运行时间（分钟）"""
    try:
        create_time = datetime.fromtimestamp(proc.create_time())
        age_minutes = (datetime.now() - create_time).total_seconds() / 60
        return age_minutes
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        return 0

def get_chrome_processes(include_all=False):
    """获取所有Chrome进程"""
    chrome_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'chrome' in proc.name().lower():
                if include_all or is_webdriver_chrome(proc):
                    chrome_processes.append(proc)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return chrome_processes

def kill_process(proc, force=False):
    """终止进程"""
    try:
        proc_info = {
            'pid': proc.pid,
            'name': proc.name(),
            'cmdline': ' '.join(proc.cmdline()) if hasattr(proc, 'cmdline') else '',
            'age': f"{get_process_age(proc):.1f} 分钟"
        }
        
        logger.info(f"终止进程: PID={proc_info['pid']}, 名称={proc_info['name']}, 运行时间={proc_info['age']}")
        
        if force:
            if platform.system() == 'Windows':
                os.kill(proc.pid, signal.SIGTERM)
            else:
                os.kill(proc.pid, signal.SIGKILL)
        else:
            proc.terminate()
            
        return True
    except Exception as e:
        logger.error(f"终止进程 {proc.pid} 失败: {e}")
        return False

def clean_chrome_processes(max_age=30, force=False, dry_run=False, include_all=False):
    """清理超过指定运行时间的Chrome进程"""
    logger.info(f"开始{'扫描' if dry_run else '清理'} Chrome 进程...")
    
    chrome_processes = get_chrome_processes(include_all)
    
    # 按运行时间排序
    chrome_processes.sort(key=get_process_age, reverse=True)
    
    total_count = len(chrome_processes)
    killed_count = 0
    
    for proc in chrome_processes:
        try:
            age_minutes = get_process_age(proc)
            
            # 如果进程运行时间超过阈值，则终止
            if age_minutes > max_age:
                if dry_run:
                    logger.info(f"[演习模式] 将终止进程: PID={proc.pid}, 名称={proc.name()}, 运行时间={age_minutes:.1f}分钟")
                else:
                    if kill_process(proc, force):
                        killed_count += 1
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    
    logger.info(f"扫描完成: 发现 {total_count} 个Chrome进程, {'将要' if dry_run else '已经'}终止 {killed_count} 个进程")
    return total_count, killed_count

def monitor_chrome_processes(interval=300, max_age=30, max_count=5):
    """持续监控Chrome进程数量，超过阈值时清理"""
    logger.info(f"启动Chrome进程监控 (间隔={interval}秒, 最大运行时间={max_age}分钟, 最大进程数={max_count})")
    
    while True:
        try:
            chrome_processes = get_chrome_processes()
            process_count = len(chrome_processes)
            
            logger.info(f"Chrome进程数量: {process_count}")
            
            # 如果进程数量超过阈值，则执行清理
            if process_count > max_count:
                logger.warning(f"Chrome进程数量 ({process_count}) 超过阈值 ({max_count})，开始清理...")
                cleaned, killed = clean_chrome_processes(max_age=max_age)
                logger.info(f"清理完成: 终止了 {killed}/{cleaned} 个Chrome进程")
            
            # 等待下一次检查
            time.sleep(interval)
            
        except KeyboardInterrupt:
            logger.info("监控已停止")
            break
        except Exception as e:
            logger.error(f"监控过程中出错: {e}")
            time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Chrome进程监控和清理工具')
    
    # 命令行参数
    parser.add_argument('--clean', action='store_true', help='清理超时的Chrome进程')
    parser.add_argument('--monitor', action='store_true', help='持续监控Chrome进程')
    parser.add_argument('--max-age', type=int, default=30, help='进程最大运行时间(分钟)')
    parser.add_argument('--max-count', type=int, default=5, help='最大允许的Chrome进程数量')
    parser.add_argument('--interval', type=int, default=300, help='监控间隔(秒)')
    parser.add_argument('--force', action='store_true', help='强制终止进程')
    parser.add_argument('--all', action='store_true', help='处理所有Chrome进程，不仅限于WebDriver启动的')
    parser.add_argument('--dry-run', action='store_true', help='演习模式，不实际终止进程')
    
    args = parser.parse_args()
    
    # 执行操作
    if args.clean:
        clean_chrome_processes(
            max_age=args.max_age, 
            force=args.force, 
            dry_run=args.dry_run,
            include_all=args.all
        )
    elif args.monitor:
        monitor_chrome_processes(
            interval=args.interval,
            max_age=args.max_age,
            max_count=args.max_count
        )
    else:
        # 默认清理操作
        chrome_count = len(get_chrome_processes(include_all=args.all))
        logger.info(f"发现 {chrome_count} 个Chrome进程")
        
        if chrome_count > 0:
            clean_chrome_processes(
                max_age=args.max_age, 
                force=args.force, 
                dry_run=args.dry_run,
                include_all=args.all
            ) 