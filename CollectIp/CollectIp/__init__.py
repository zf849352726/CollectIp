from __future__ import absolute_import, unicode_literals

# 这将确保在Django启动时加载Celery app
from .celery import app as celery_app

__all__ = ('celery_app',)

import pymysql
pymysql.install_as_MySQLdb()