from django.apps import AppConfig
import os

class IpOperatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ip_operator'
    verbose_name = 'IP代理池管理'

    def ready(self):
        """当Django启动时初始化定时任务"""
        from django.conf import settings
        import os
        
        # 确保日志目录存在
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        if not settings.DEBUG or os.environ.get('RUN_MAIN', None) == 'true':
            from . import scheduler
            scheduler.start() 