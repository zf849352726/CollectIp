"""
修复ProxySettings表的字段问题
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CollectIp.settings')
django.setup()

# 导入必要的模型
from django.db import connection

def fix_proxy_settings():
    """修复ProxySettings表"""
    print("开始修复ProxySettings表...")
    
    # 检查auto_crawler和auto_score字段是否存在
    with connection.cursor() as cursor:
        # 获取表结构信息
        cursor.execute("PRAGMA table_info(proxy_settings)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        # 检查是否需要添加auto_crawler字段
        if 'auto_crawler' not in column_names:
            print("添加auto_crawler字段...")
            cursor.execute("ALTER TABLE proxy_settings ADD COLUMN auto_crawler BOOLEAN DEFAULT 0")
            
        # 检查是否需要添加auto_score字段
        if 'auto_score' not in column_names:
            print("添加auto_score字段...")
            cursor.execute("ALTER TABLE proxy_settings ADD COLUMN auto_score BOOLEAN DEFAULT 0")
    
    # 确保至少有一条记录
    from index.models import ProxySettings
    settings, created = ProxySettings.objects.get_or_create(
        id=1,
        defaults={
            'crawler_interval': 3600,
            'score_interval': 1800,
            'min_score': 10,
            'auto_crawler': False,
            'auto_score': False
        }
    )
    
    if created:
        print("创建了新的ProxySettings记录")
    else:
        print(f"更新现有ProxySettings记录: {settings.id}")
        # 确保auto_crawler和auto_score字段有值
        if not hasattr(settings, 'auto_crawler') or settings.auto_crawler is None:
            settings.auto_crawler = False
        if not hasattr(settings, 'auto_score') or settings.auto_score is None:
            settings.auto_score = False
        settings.save()
    
    print("ProxySettings表修复完成")
    
    # 显示当前设置
    print("\n当前设置:")
    print(f"爬虫间隔: {settings.crawler_interval}秒")
    print(f"评分间隔: {settings.score_interval}秒")
    print(f"最低分数: {settings.min_score}")
    print(f"自动爬虫: {'启用' if settings.auto_crawler else '禁用'}")
    print(f"自动评分: {'启用' if settings.auto_score else '禁用'}")

if __name__ == "__main__":
    fix_proxy_settings() 