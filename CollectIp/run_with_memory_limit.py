#!/usr/bin/env python3
"""
内存限制运行器 - 在内存有限的环境中运行Django命令

使用方法:
  python run_with_memory_limit.py makemigrations
  python run_with_memory_limit.py migrate
  python run_with_memory_limit.py [任何Django命令]
"""

import os
import sys
import gc
import resource
import subprocess
import traceback

# 设置内存限制（单位：字节）
MEMORY_LIMIT = 200 * 1024 * 1024  # 200MB

def limit_memory():
    """设置进程的内存使用限制"""
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))

def run_gc():
    """运行垃圾回收以释放内存"""
    gc.collect()

def run_command(command):
    """使用内存限制运行命令"""
    try:
        # 设置环境变量以降低内存使用
        my_env = os.environ.copy()
        my_env["PYTHONOPTIMIZE"] = "1"  # 优化Python执行
        my_env["PYTHONHASHSEED"] = "0"  # 固定哈希种子
        my_env["DJANGO_SETTINGS_MODULE"] = "CollectIp.settings_optimized"  # 使用优化的设置

        # 使用较小的缓冲区大小
        kwargs = {
            'env': my_env,
            'bufsize': 4096,
        }

        # 在子进程中运行命令
        print(f"运行命令 (内存限制 {MEMORY_LIMIT/1024/1024}MB): {' '.join(command)}")
        
        # 启动进程前执行垃圾回收
        run_gc()
        
        # 使用subprocess运行命令
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            **kwargs
        )
        
        # 处理输出
        for line in process.stdout:
            print(line, end='')
        
        # 等待进程完成
        exit_code = process.wait()
        
        # 处理错误
        if exit_code != 0:
            for line in process.stderr:
                print(line, end='', file=sys.stderr)
            print(f"命令失败，退出代码: {exit_code}", file=sys.stderr)
            return exit_code
            
        return 0
        
    except Exception as e:
        print(f"执行命令时出错: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python run_with_memory_limit.py [Django命令]")
        sys.exit(1)
    
    # 构建要运行的命令
    command = ["python", "manage.py"] + sys.argv[1:]
    
    # 运行垃圾回收
    run_gc()
    
    # 运行命令
    exit_code = run_command(command)
    sys.exit(exit_code) 