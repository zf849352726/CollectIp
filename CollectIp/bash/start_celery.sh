#!/bin/bash
# 启动Celery Worker的脚本

# 设置项目根目录
PROJECT_ROOT=$(cd "$(dirname "$0")/../../" && pwd)
echo "项目根目录: $PROJECT_ROOT"

# 检查虚拟环境
VENV_PATH="/usr/local/venv/djangoLearn"
if [ -f "$VENV_PATH/bin/activate" ]; then
    echo "激活虚拟环境: $VENV_PATH"
    source "$VENV_PATH/bin/activate"
else
    echo "警告: 虚拟环境 $VENV_PATH 不存在或无法访问"
fi

# 切换到项目目录
cd "$PROJECT_ROOT" || {
    echo "错误: 无法切换到项目目录: $PROJECT_ROOT"
    exit 1
}

# 显示Python和Django版本
echo "Python版本:"
python --version
echo "Django版本:"
python -c "import django; print(django.get_version())"
echo "Celery版本:"
python -c "import celery; print(celery.__version__)"

# 检查Redis是否可用
echo "检查Redis连接..."
if ! command -v redis-cli &>/dev/null; then
    echo "警告: redis-cli 命令不可用，无法检查Redis状态"
else
    if redis-cli ping | grep -q "PONG"; then
        echo "Redis连接正常"
    else
        echo "错误: 无法连接到Redis，请确保Redis服务已启动"
        exit 1
    fi
fi

# 设置环境变量
export DJANGO_SETTINGS_MODULE=CollectIp.settings

# 启动Celery Worker
echo "启动Celery Worker..."

# 获取命令行参数
CONCURRENCY=${1:-2}  # 默认并发数为2
LOGLEVEL=${2:-info}  # 默认日志级别为info

# 创建日志目录
mkdir -p "$PROJECT_ROOT/logs"

# 查找并终止之前运行的Celery进程
echo "检查是否有已运行的Celery进程..."
pkill -f "celery -A CollectIp worker" || echo "没有找到运行中的Celery进程"

# 启动新的Celery Worker
echo "启动Celery Worker (并发数: $CONCURRENCY, 日志级别: $LOGLEVEL)..."
nohup celery -A CollectIp worker --loglevel=$LOGLEVEL --concurrency=$CONCURRENCY > "$PROJECT_ROOT/logs/celery.log" 2>&1 &

# 获取进程ID
CELERY_PID=$!
echo "Celery Worker已启动，PID: $CELERY_PID"

# 启动Celery Beat (可选，用于定时任务)
if [ "$3" == "beat" ]; then
    echo "同时启动Celery Beat..."
    pkill -f "celery -A CollectIp beat" || echo "没有找到运行中的Celery Beat进程"
    nohup celery -A CollectIp beat --loglevel=$LOGLEVEL > "$PROJECT_ROOT/logs/celery_beat.log" 2>&1 &
    BEAT_PID=$!
    echo "Celery Beat已启动，PID: $BEAT_PID"
fi

echo "启动完成!"
echo "Celery日志路径: $PROJECT_ROOT/logs/celery.log"
if [ "$3" == "beat" ]; then
    echo "Celery Beat日志路径: $PROJECT_ROOT/logs/celery_beat.log"
fi 