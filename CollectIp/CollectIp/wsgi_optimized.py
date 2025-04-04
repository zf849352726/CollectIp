"""
WSGI config for CollectIp project - Memory Optimized Version.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# 使用优化的设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CollectIp.settings_optimized')

application = get_wsgi_application() 