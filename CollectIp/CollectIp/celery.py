import os
from celery import Celery

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CollectIp.settings')

# 创建Celery实例
app = Celery('CollectIp')

# 使用Django的settings.py中的配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 加载Beat定时任务配置
try:
    from ip_operator.celery_beat_schedule import CELERYBEAT_SCHEDULE
    app.conf.beat_schedule = CELERYBEAT_SCHEDULE
    print("已加载Celery Beat定时任务配置")
except ImportError:
    print("警告: 无法导入Celery Beat定时任务配置")

# 自动发现任务
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 