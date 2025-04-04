# Database - 优化数据库连接
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'collectipdb',
        'USER': 'root',
        'PASSWORD': 'Usb04usb.com',  # 更新为新设置的MySQL密码
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