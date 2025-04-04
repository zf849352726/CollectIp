# gunicorn_config.py
# 内存优化的Gunicorn配置，适用于低内存VPS

# 绑定的IP和端口
bind = "127.0.0.1:8000"

# 工作进程类型 - 使用gevent异步以减少内存占用
worker_class = "gevent"

# 工作进程数量 - 设置为较小的值，适合内存小的服务器
workers = 1  # 对于内存非常有限的服务器，使用单进程

# 工作进程的线程数 - 增加线程而不是进程以减少内存占用
threads = 4

# 超时时间
timeout = 60

# 最大请求数，达到此数值后自动重启工作进程以释放内存
max_requests = 500
max_requests_jitter = 50

# 保持工作进程的存活
keepalive = 5

# 日志级别 - 设置为警告以减少日志量
loglevel = "warning"

# 日志文件
errorlog = "/usr/local/CollectIp/logs/gunicorn-error.log"
accesslog = "/usr/local/CollectIp/logs/gunicorn-access.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 预加载应用以减少启动时间
preload_app = True

# 启动时静默
capture_output = True

# 守护进程模式 - 后台运行
daemon = True

# PID文件
pidfile = "/usr/local/CollectIp/gunicorn.pid"

# 内存限制器（非官方配置，需要通过系统cgroup或ulimit设置）
# 这里只是作为注释提供信息
# 推荐通过systemd服务配置设置内存限制:
# [Service]
# MemoryLimit=256M

# 优化的钩子函数
def on_starting(server):
    """在Gunicorn启动前执行"""
    import gc
    gc.collect()  # 启动前进行一次垃圾回收

def on_exit(server):
    """在Gunicorn退出前执行"""
    import gc
    gc.collect()  # 退出前进行一次垃圾回收

def post_fork(server, worker):
    """在工作进程启动后执行"""
    import gc
    gc.collect()  # Fork后进行一次垃圾回收

def worker_abort(worker):
    """在工作进程终止前执行"""
    import gc
    gc.collect()  # 终止前进行一次垃圾回收 