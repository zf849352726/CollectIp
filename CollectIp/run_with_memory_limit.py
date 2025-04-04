#!/usr/bin/env python3
"""
内存限制运行器 - 在内存有限的环境中运行Django命令

使用方法:
  python run_with_memory_limit.py makemigrations
  python run_with_memory_limit.py migrate
  python run_with_memory_limit.py [任何Django命令]
  
  可以使用 --memory-limit 参数调整内存限制，例如:
  python run_with_memory_limit.py --memory-limit 300 check
"""

import os
import sys
import gc
import resource
import subprocess
import traceback
import argparse

# 默认内存限制（单位：MB）
DEFAULT_MEMORY_LIMIT_MB = 300  # 调整为300MB

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='在内存限制下运行Django命令')
    parser.add_argument('--memory-limit', type=int, default=DEFAULT_MEMORY_LIMIT_MB,
                        help=f'内存限制（MB），默认 {DEFAULT_MEMORY_LIMIT_MB}MB')
    # 获取Django命令
    args, django_args = parser.parse_known_args()
    return args, django_args

def limit_memory(memory_limit_mb):
    """设置进程的内存使用限制"""
    memory_limit = memory_limit_mb * 1024 * 1024  # 转换为字节
    try:
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
        return True
    except Exception as e:
        print(f"警告: 无法设置内存限制: {e}", file=sys.stderr)
        return False

def run_gc():
    """运行垃圾回收以释放内存"""
    collected = gc.collect()
    print(f"释放了 {collected} 个对象")

def optimize_python():
    """设置优化Python运行时的环境变量"""
    # 使用优化模式运行Python
    os.environ["PYTHONOPTIMIZE"] = "2"
    
    # 固定哈希种子可减少内存碎片
    os.environ["PYTHONHASHSEED"] = "0"
    
    # 使用优化的设置模块
    os.environ["DJANGO_SETTINGS_MODULE"] = "CollectIp.settings_optimized"
    
    # 关闭Python的调试分配器
    os.environ["PYTHONMALLOC"] = "malloc"
    
    # 限制递归深度
    sys.setrecursionlimit(1000)

def run_command(command, memory_limit_mb):
    """使用内存限制运行命令"""
    try:
        # 优化Python运行时
        optimize_python()
        
        # 复制环境变量
        my_env = os.environ.copy()
        
        # 使用较小的缓冲区大小
        kwargs = {
            'env': my_env,
            'bufsize': 4096,
        }

        # 在子进程中运行命令
        print(f"运行命令 (内存限制 {memory_limit_mb}MB): {' '.join(command)}")
        
        # 运行垃圾回收
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
            sys.stdout.flush()  # 立即刷新输出
        
        # 等待进程完成
        exit_code = process.wait()
        
        # 处理错误
        if exit_code != 0:
            error_output = process.stderr.read()
            if error_output:
                print(error_output, file=sys.stderr)
            
            if exit_code == -9:
                print("进程被终止，可能是因为内存不足。尝试增加内存限制：", file=sys.stderr)
                print(f"  python run_with_memory_limit.py --memory-limit {memory_limit_mb + 100} {' '.join(command[2:])}", file=sys.stderr)
            else:
                print(f"命令失败，退出代码: {exit_code}", file=sys.stderr)
            
            return exit_code
            
        return 0
        
    except Exception as e:
        print(f"执行命令时出错: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # 解析参数
    args, django_args = parse_args()
    
    if not django_args:
        print("用法: python run_with_memory_limit.py [--memory-limit MB] [Django命令]")
        sys.exit(1)
    
    # 构建要运行的命令
    command = ["python", "manage.py"] + django_args
    
    # 设置内存限制
    limit_success = limit_memory(args.memory_limit)
    if not limit_success:
        print("将在没有内存限制的情况下运行命令", file=sys.stderr)
    
    # 运行垃圾回收
    run_gc()
    
    # 运行命令
    exit_code = run_command(command, args.memory_limit)
    sys.exit(exit_code) 