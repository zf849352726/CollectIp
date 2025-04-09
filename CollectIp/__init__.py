"""
#!/usr/bin/env python
# -*- coding:utf-8 -*-
@Project : CollectIp
@File : __init__.py
@Author : 帅张张
@Time : 2025/3/23 21:43

"""
from __future__ import absolute_import, unicode_literals

# 这将确保在Django启动时加载Celery app
from .CollectIp.celery import app as celery_app

__all__ = ('celery_app',)

import pymysql
pymysql.install_as_MySQLdb()