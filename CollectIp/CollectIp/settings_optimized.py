"""
Django settings for CollectIp project - Memory Optimized Version.

内存优化版本 - 适用于资源有限的Linux服务器
"""

from pathlib import Path
import os
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-2ockpy=7#hbuh4!a=01@we$*vko#j-xp$4w+9w73u+!u#ml)55'

# 在生产环境关闭DEBUG以减少内存使用
DEBUG = False

# 允许所有主机连接，或指定您的域名
ALLOWED_HOSTS = ['*']

# Application definition - 只保留必要的应用
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'index',
    'ip_operator.apps.IpOperatorConfig',
    # 'debug_toolbar', # 在生产环境移除调试工具栏
]

# 减少中间件数量以优化内存使用
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware', # 可选
    # 'debug_toolbar.middleware.DebugToolbarMiddleware', # 移除调试工具栏
]

# 设置URL配置为优化版本
ROOT_URLCONF = 'CollectIp.urls_optimized'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'CollectIp.wsgi.application'

# Database - 优化数据库连接
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'collectipdb',
        'USER': 'root',
        'PASSWORD': '123456',  # 更新为新设置的MySQL密码
        'HOST': '127.0.0.1',
        'PORT': '3306',
        # 添加连接池优化
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
        # 减少连接数以节省内存
        'CONN_MAX_AGE': 600,  # 连接复用时间（秒）
        'CONN_HEALTH_CHECKS': False,  # 禁用健康检查以减少开销
    },
    'mongodb': {
        'ENGINE': 'djongo',
        'NAME': 'collectip_comments',
        'CLIENT': {
            'host': 'localhost',
            'port': 27017,
            'username': '',
            'password': '',
            'authSource': 'admin',
            # 减少默认连接池大小
            'maxPoolSize': 5,
            'minPoolSize': 1,
        }
    }
}

# 减少密码验证器数量以优化内存
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
]

# Internationalization
LANGUAGE_CODE = 'zh-Hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = False

# 静态文件配置 - 生产环境使用
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# 移除STATICFILES_DIRS以优化内存使用
# STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 媒体文件配置
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# 登录相关配置
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/ip_pool/'
LOGOUT_REDIRECT_URL = '/login/'

# 会话配置 - 优化会话处理以减少内存使用
SESSION_ENGINE = 'django.contrib.sessions.backends.file'  # 使用文件而不是数据库/缓存
SESSION_COOKIE_AGE = 86400  # 降低为1天
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # 关闭浏览器时清除session

# 缓存配置 - 使用文件缓存以减少内存使用
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(BASE_DIR, 'django_cache'),
        'TIMEOUT': 60,  # 降低缓存超时时间
        'OPTIONS': {
            'MAX_ENTRIES': 1000,  # 限制缓存条目数量
        }
    }
}

# IP池配置 - 降低并发请求数
IP_POOL_CONFIG = {
    'CRAWLER_INTERVAL': 3600,
    'SCORE_INTERVAL': 1800,
    'MIN_SCORE': 10,
    'TEST_URLS': [
        'http://www.baidu.com',
    ],
    'CRAWLER': {
        'USER_AGENT': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
        'DOWNLOAD_DELAY': 3,  # 增加下载延迟以减少资源使用
        'CONCURRENT_REQUESTS': 4,  # 降低并发请求数
    }
}

# 确保logs目录存在
if not os.path.exists(os.path.join(BASE_DIR, 'logs')):
    os.makedirs(os.path.join(BASE_DIR, 'logs'))

# 日志配置 - 优化以减少磁盘IO和内存使用
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,  # 禁用现有的日志记录器
    'formatters': {
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',  # 只记录警告和错误
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.log'),
            'maxBytes': 5 * 1024 * 1024,  # 5MB
            'backupCount': 3,
            'formatter': 'simple',
            'delay': True,
        },
        'ip_operator': {
            'level': 'WARNING',  # 只记录警告和错误
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/ip_operator.log'),
            'maxBytes': 5 * 1024 * 1024,  # 5MB
            'backupCount': 3,
            'formatter': 'simple',
            'delay': True,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'ip_operator': {
            'handlers': ['ip_operator'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# 减少文件上传处理的内存使用
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5MB 