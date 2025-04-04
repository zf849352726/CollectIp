#!/usr/bin/env python3
"""
临时检查脚本 - 在不加载SnowNLP的情况下运行Django check命令

使用方法:
  python check_django.py
"""

import os
import sys
import subprocess
import shutil
import time

def backup_file(file_path):
    """创建文件备份"""
    backup_path = file_path + '.bak'
    if os.path.exists(file_path):
        shutil.copy2(file_path, backup_path)
        print(f"已创建备份: {backup_path}")
        return True
    return False

def restore_file(file_path):
    """从备份恢复文件"""
    backup_path = file_path + '.bak'
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, file_path)
        os.remove(backup_path)
        print(f"已从备份恢复: {file_path}")
        return True
    return False

def modify_views_file():
    """修改views.py文件，使用简化版本的text_utils"""
    views_path = 'index/views.py'
    
    # 读取原文件内容
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换导入语句
    modified_content = content.replace(
        'from index.text_utils import TextProcessor',
        'from index.text_utils_simple import TextProcessor'
    )
    
    # 写回文件
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print("已修改views.py文件，使用简化版本的TextProcessor")

def run_django_check():
    """运行Django check命令"""
    print("运行Django check命令...")
    
    # 设置Django设置模块
    os.environ["DJANGO_SETTINGS_MODULE"] = "CollectIp.settings_optimized"
    
    # 使用subprocess运行命令
    result = subprocess.run([sys.executable, 'manage.py', 'check'], 
                           capture_output=True, 
                           text=True)
    
    print("\n=== 输出 ===")
    print(result.stdout)
    
    if result.stderr:
        print("\n=== 错误 ===")
        print(result.stderr)
    
    print(f"\n命令退出代码: {result.returncode}")
    return result.returncode == 0

def main():
    """主函数"""
    views_path = 'index/views.py'
    
    print("=== 开始临时检查脚本 ===")
    
    # 备份原始文件
    if not backup_file(views_path):
        print(f"错误: 无法找到文件 {views_path}")
        return 1
    
    try:
        # 修改文件
        modify_views_file()
        
        # 运行检查
        success = run_django_check()
        
        if success:
            print("\n✅ Django检查成功!")
        else:
            print("\n❌ Django检查失败!")
            
    except Exception as e:
        print(f"发生错误: {e}")
        return 1
    finally:
        # 恢复原始文件
        restore_file(views_path)
        print("=== 临时检查脚本完成 ===")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 