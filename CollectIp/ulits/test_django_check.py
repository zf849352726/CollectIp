#!/usr/bin/env python3
"""
测试Django check命令

此脚本测试禁用SnowNLP后Django check命令是否能正常运行
"""

import os
import sys
import subprocess
import importlib

def run_check_command():
    """运行Django check命令"""
    print("==========================================")
    print(" 测试禁用SnowNLP后Django check命令 ")
    print("==========================================")

    # 设置Django设置模块
    os.environ["DJANGO_SETTINGS_MODULE"] = "CollectIp.settings_optimized"
    
    # 确认TextProcessor不再使用SnowNLP
    try:
        from CollectIp.ulits.text_utils import TextProcessor
        
        # 尝试进行简单情感分析
        sentiment, score = TextProcessor.analyze_sentiment("这个项目很棒")
        print(f"情感分析测试结果: sentiment={sentiment}, score={score}")
        print("✅ 情感分析功能正常，不使用SnowNLP")
    except ImportError as e:
        if "SnowNLP" in str(e):
            print(f"❌ 仍然尝试导入SnowNLP: {e}")
            return False
        else:
            print(f"❌ 导入错误: {e}")
            return False
    except Exception as e:
        print(f"❌ 测试情感分析时出错: {e}")
        return False
    
    print("\n运行Django check命令...")
    
    # 使用subprocess运行命令
    result = subprocess.run([sys.executable, 'manage.py', 'check'], 
                           capture_output=True, 
                           text=True)
    
    print("\n=== 命令输出 ===")
    print(result.stdout)
    
    if result.stderr:
        print("\n=== 错误输出 ===")
        print(result.stderr)
    
    success = result.returncode == 0
    
    if success:
        print("\n✅ Django检查成功!")
    else:
        print(f"\n❌ Django检查失败! 退出代码: {result.returncode}")
    
    return success

if __name__ == "__main__":
    success = run_check_command()
    sys.exit(0 if success else 1) 