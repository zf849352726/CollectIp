"""
Celery Beat定时任务配置
"""
from celery.schedules import crontab
from django.conf import settings

# 从Django设置中获取爬虫间隔时间（默认为1小时）
CRAWLER_INTERVAL = getattr(settings, 'IP_POOL_CONFIG', {}).get('CRAWLER_INTERVAL', 3600)
SCORE_INTERVAL = getattr(settings, 'IP_POOL_CONFIG', {}).get('SCORE_INTERVAL', 1800)

# 将秒转换为分钟
CRAWLER_MINUTES = max(1, int(CRAWLER_INTERVAL / 60))
SCORE_MINUTES = max(1, int(SCORE_INTERVAL / 60))

# 定时任务配置
CELERYBEAT_SCHEDULE = {
    # 定期爬取IP代理
    'crawl-ip-every-hour': {
        'task': 'ip_operator.tasks.crawl_ip_task',
        'schedule': crontab(minute=f'*/{CRAWLER_MINUTES}'),  # 每x分钟执行一次
        'args': ('all',),
        'options': {
            'expires': CRAWLER_INTERVAL  # 任务过期时间
        }
    },
    
    # 定期爬取热门电影（示例）
    'crawl-hot-movies-daily': {
        'task': 'ip_operator.tasks.crawl_douban_task',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点执行
        'args': ('热门电影',),
        'kwargs': {
            'strategy': 'random',
            'max_pages': 5
        },
        'options': {
            'expires': 86400  # 24小时过期
        }
    },
    
    # 其他定时任务可以在这里添加
} 