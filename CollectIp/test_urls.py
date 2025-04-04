#!/usr/bin/env python
"""
URL配置测试脚本
用于验证优化版URL配置是否正常工作
"""
import os
import sys

# 设置Django环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CollectIp.settings_optimized")
import django
django.setup()

# 导入URL相关模块
from django.urls import resolve, reverse
from django.urls.exceptions import Resolver404
from django.core.exceptions import ImproperlyConfigured

def test_urls():
    """测试URL配置是否正常工作"""
    print("测试URL配置...")
    
    # 测试基本URL
    test_cases = [
        '/',
        '/login/',
        '/register/',
        '/ip_pool/',
        '/ip_pool/manage/',
        '/proxy_settings/'
    ]
    
    success = 0
    failure = 0
    
    for url in test_cases:
        try:
            # 尝试解析URL
            resolved = resolve(url)
            print(f"✅ URL '{url}' 解析成功: {resolved.view_name}")
            success += 1
        except Resolver404:
            print(f"❌ URL '{url}' 解析失败: 未找到匹配的模式")
            failure += 1
        except ImproperlyConfigured as e:
            print(f"❌ URL '{url}' 解析失败: 配置错误 - {str(e)}")
            failure += 1
        except Exception as e:
            print(f"❌ URL '{url}' 解析失败: {str(e)}")
            failure += 1
    
    print(f"\n总计测试: {success + failure}, 成功: {success}, 失败: {failure}")
    
    if failure > 0:
        print("\n请检查urls_optimized.py文件中的URL配置是否正确")
    else:
        print("\nURL配置测试通过，可以继续部署")

if __name__ == "__main__":
    try:
        test_urls()
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        sys.exit(1) 