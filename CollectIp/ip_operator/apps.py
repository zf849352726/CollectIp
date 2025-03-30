from django.apps import AppConfig
import os
import time

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
        
        # 只在主进程中启动调度器
        if not settings.DEBUG or os.environ.get('RUN_MAIN', None) == 'true':
            # 使用文件锁确保只有一个进程启动调度器
            lock_file = os.path.join(settings.BASE_DIR, 'scheduler.lock')
            if os.path.exists(lock_file):
                # 检查锁文件是否过期（超过1小时）
                if os.path.getmtime(lock_file) < (time.time() - 3600):
                    os.remove(lock_file)
                else:
                    return  # 锁文件存在且未过期，不启动调度器
                    
            # 创建锁文件
            try:
                with open(lock_file, 'w') as f:
                    f.write(str(os.getpid()))
                    
                # 启动调度器
                from . import scheduler
                scheduler.start()
            except Exception as e:
                import logging
                logger = logging.getLogger('ip_operator')
                logger.error(f"启动调度器时出错: {e}")
                if os.path.exists(lock_file):
                    os.remove(lock_file) 