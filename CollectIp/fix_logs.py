#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志修复工具
可以用来修复因为文件占用导致的日志问题
"""

import os
import sys
import time
import shutil
import psutil
from pathlib import Path

def is_file_locked(filepath):
    """
    检查文件是否被锁定
    """
    if not os.path.exists(filepath):
        return False
        
    # 尝试以写入方式打开文件
    try:
        with open(filepath, 'a'):
            pass
        return False
    except (IOError, PermissionError):
        return True

def find_process_locking_file(filepath):
    """
    查找锁定文件的进程
    """
    if not os.path.exists(filepath):
        return []
        
    locked_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'open_files']):
        try:
            open_files = proc.open_files()
            if open_files:
                for open_file in open_files:
                    if os.path.abspath(open_file.path) == os.path.abspath(filepath):
                        locked_processes.append({
                            'pid': proc.pid,
                            'name': proc.name(),
                            'cmd': ' '.join(proc.cmdline()) if hasattr(proc, 'cmdline') else 'Unknown'
                        })
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    
    return locked_processes

def backup_log_file(filepath):
    """
    备份日志文件
    """
    if not os.path.exists(filepath):
        return None
        
    backup_path = f"{filepath}.bak.{int(time.time())}"
    try:
        shutil.copy2(filepath, backup_path)
        print(f"已备份日志文件到: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"备份文件失败: {e}")
        return None

def rename_locked_log(filepath):
    """
    重命名被锁定的日志文件
    """
    if not os.path.exists(filepath):
        return None
        
    renamed_path = f"{filepath}.locked.{int(time.time())}"
    try:
        os.rename(filepath, renamed_path)
        print(f"已重命名锁定的日志文件为: {renamed_path}")
        return renamed_path
    except Exception as e:
        print(f"重命名文件失败: {e}")
        return None

def main():
    # 项目根目录
    project_dir = Path(__file__).resolve().parent
    
    # 日志目录
    logs_dir = project_dir / 'CollectIp' / 'logs'
    
    if not logs_dir.exists():
        print(f"日志目录不存在: {logs_dir}")
        os.makedirs(logs_dir)
        print(f"已创建日志目录: {logs_dir}")
        return
    
    print(f"检查日志目录: {logs_dir}")
    
    # 遍历日志文件
    for log_file in logs_dir.glob('*.log'):
        file_path = str(log_file)
        print(f"检查日志文件: {file_path}")
        
        if is_file_locked(file_path):
            print(f"文件被锁定: {file_path}")
            
            # 查找锁定进程
            locking_processes = find_process_locking_file(file_path)
            if locking_processes:
                print("以下进程正在使用此文件:")
                for proc in locking_processes:
                    print(f"PID: {proc['pid']}, 名称: {proc['name']}, 命令: {proc['cmd']}")
                
                # 询问用户是否终止进程
                user_input = input("是否终止这些进程? (y/n): ")
                if user_input.lower() == 'y':
                    for proc in locking_processes:
                        try:
                            psutil.Process(proc['pid']).terminate()
                            print(f"已终止进程: {proc['pid']}")
                        except Exception as e:
                            print(f"终止进程失败: {e}")
                    
                    # 等待进程结束
                    time.sleep(1)
                    
                    # 再次检查是否仍被锁定
                    if is_file_locked(file_path):
                        print(f"文件仍被锁定，尝试重命名...")
                        renamed_path = rename_locked_log(file_path)
                        if renamed_path:
                            # 创建一个空的新文件
                            with open(file_path, 'w') as f:
                                pass
                            print(f"已创建新的空日志文件: {file_path}")
                    else:
                        print(f"文件已解锁: {file_path}")
                        
                else:
                    # 用户选择不终止进程，备份并重命名
                    backup_log_file(file_path)
                    renamed_path = rename_locked_log(file_path)
                    
                    if renamed_path:
                        # 创建一个空的新文件
                        with open(file_path, 'w') as f:
                            pass
                        print(f"已创建新的空日志文件: {file_path}")
            else:
                print("未找到锁定此文件的进程，尝试重命名文件...")
                backup_log_file(file_path)
                renamed_path = rename_locked_log(file_path)
                
                if renamed_path:
                    # 创建一个空的新文件
                    with open(file_path, 'w') as f:
                        pass
                    print(f"已创建新的空日志文件: {file_path}")
        else:
            print(f"文件未被锁定: {file_path}")
            
            # 检查是否有备份文件需要清理
            backup_files = list(logs_dir.glob(f"{log_file.name}.bak.*"))
            if backup_files:
                print(f"找到 {len(backup_files)} 个备份文件")
                if len(backup_files) > 3:  # 保留最近的3个备份
                    # 按修改时间排序
                    backup_files.sort(key=lambda x: os.path.getmtime(x))
                    
                    # 删除旧的备份
                    for old_backup in backup_files[:-3]:
                        try:
                            os.remove(old_backup)
                            print(f"已删除旧备份: {old_backup}")
                        except Exception as e:
                            print(f"删除旧备份失败: {e}")
    
    print("日志文件检查完成")

if __name__ == "__main__":
    main() 