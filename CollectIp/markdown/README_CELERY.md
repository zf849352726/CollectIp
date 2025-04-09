# Celery + Redis + Subprocess 爬虫管理系统

本文档介绍如何使用 Celery、Redis 和 Subprocess 来管理和运行爬虫任务。

## 系统架构

系统使用以下组件：

1. **Celery**：分布式任务队列系统，用于管理爬虫任务
2. **Redis**：作为消息代理和结果存储后端
3. **Subprocess**：在子进程中运行爬虫，确保爬虫崩溃不影响主应用

## 安装依赖

```bash
pip install celery redis psutil
```

## 启动服务

### 1. 启动 Redis 服务

```bash
# 在 Linux 上
sudo systemctl start redis

# 在 Windows 上
# 1. 下载 Redis for Windows
# 2. 运行 redis-server.exe
```

### 2. 启动 Celery Worker

```bash
# 使用提供的脚本（推荐）
bash CollectIp/ulits/start_celery.sh

# 或者手动启动
cd /path/to/project
celery -A CollectIp worker --loglevel=info
```

### 3. 启动 Celery Beat （用于定时任务）

```bash
# 使用提供的脚本并添加 beat 参数
bash CollectIp/ulits/start_celery.sh 2 info beat

# 或者手动启动
cd /path/to/project
celery -A CollectIp beat --loglevel=info
```

## 使用方法

### 在 Python 代码中使用

```python
# 启动 IP 爬虫
from ip_operator.services.celery_crawler import start_crawl_ip

# 启动爬虫并获取任务对象
task = start_crawl_ip(crawl_type="all")

# 检查任务状态
from ip_operator.services.celery_crawler import check_task_status
status = check_task_status(task.id)
print(f"任务状态: {status['status']}")

# 启动豆瓣电影评论爬虫
from ip_operator.services.celery_crawler import start_crawl_douban
task = start_crawl_douban(
    movie_name="霸王别姬",
    strategy="sequential",
    max_pages=2
)

# 获取所有正在运行的爬虫
from ip_operator.services.celery_crawler import get_all_running_spiders
running_spiders = get_all_running_spiders()
print(f"正在运行的爬虫: {running_spiders}")

# 停止爬虫
from ip_operator.services.celery_crawler import stop_running_spider
stop_running_spider('douban_spider', {'movie_name': '霸王别姬'})
```

### 在 Django 视图中使用

```python
from django.http import JsonResponse
from ip_operator.services.celery_crawler import start_crawl_douban, check_task_status

def start_movie_crawler(request):
    movie_name = request.POST.get('movie_name')
    if not movie_name:
        return JsonResponse({'success': False, 'message': '电影名称不能为空'})
    
    # 启动爬虫任务
    task = start_crawl_douban(
        movie_name=movie_name,
        strategy='sequential',
        max_pages=2
    )
    
    if task:
        return JsonResponse({
            'success': True,
            'message': f'爬虫任务已提交，任务ID: {task.id}',
            'task_id': task.id
        })
    else:
        return JsonResponse({
            'success': False,
            'message': '爬虫任务已在运行或启动失败'
        })

def check_crawler_status(request):
    task_id = request.GET.get('task_id')
    if not task_id:
        return JsonResponse({'success': False, 'message': '任务ID不能为空'})
    
    status = check_task_status(task_id)
    return JsonResponse({
        'success': True,
        'status': status
    })
```

## 优点和特性

1. **可靠性**：使用Redis锁机制确保同一爬虫不会重复运行
2. **可伸缩性**：可以轻松扩展到多台服务器
3. **隔离性**：爬虫在子进程中运行，崩溃不影响主应用
4. **监控能力**：可以实时监控爬虫状态
5. **重试机制**：任务失败时自动重试
6. **定时任务**：支持定期执行爬虫任务

## 注意事项

1. 确保 Redis 服务已启动并可访问
2. 爬虫超时时间默认为1小时，可在设置中修改
3. 如需添加新的爬虫，请在 `tasks.py` 中创建相应的任务函数
4. 爬虫的日志保存在 `logs` 目录下