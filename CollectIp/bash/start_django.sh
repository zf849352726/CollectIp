#!/bin/bash

# 脚本名称: start_django.sh
# 功能: 激活虚拟环境并启动Django应用
# 作者: 系统管理员
# 日期: 2025-04-05

# 定义项目根目录
PROJECT_ROOT="/var/www/collectip"
if [ ! -d "$PROJECT_ROOT" ]; then
    # 如果指定目录不存在，使用当前脚本相对路径
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
fi

echo "======================================================"
echo "        Django应用启动脚本 - CollectIp项目            "
echo "======================================================"
echo "项目根目录: $PROJECT_ROOT"

# 进入项目目录
cd "$PROJECT_ROOT"
echo "当前工作目录: $(pwd)"

# 激活虚拟环境
echo "正在激活虚拟环境..."
if [ -f "/usr/local/venv/djangoLearn/bin/activate" ]; then
    source /usr/local/venv/djangoLearn/bin/activate
    
    # 判断是否成功激活
    if [ $? -eq 0 ]; then
        echo "虚拟环境已成功激活!"
        echo "Python路径: $(which python)"
        echo "Python版本: $(python --version)"
    else
        echo "虚拟环境激活失败!"
        exit 1
    fi
else
    echo "错误: 虚拟环境文件不存在!"
    echo "请检查路径: /usr/local/venv/djangoLearn/bin/activate"
    exit 1
fi

# 初始化环境变量
export DJANGO_SETTINGS_MODULE=CollectIp.settings
echo "设置环境变量: DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"

# 检查Django项目
echo "检查Django项目..."
python manage.py check

# 收集静态文件
echo "收集静态文件..."
python manage.py collectstatic --noinput
# 启动Django服务器
echo "正在启动Django应用服务器..."
echo "======================================================"
echo "请选择启动模式:"
echo "1) 开发环境 - 使用Django内置服务器"
echo "2) 生产环境 - 使用Gunicorn"
echo "3) 调试模式 - 使用Django内置服务器(DEBUG=True)"
echo "4) 测试模式 - 运行测试套件"
read -p "请输入选项 [1-4] (默认: 1): " choice

case $choice in
    2)
        echo "生产环境模式 - 使用Gunicorn"
        gunicorn --bind 0.0.0.0:8000 CollectIp.wsgi:application
        ;;
    3)
        echo "调试模式 - 使用Django内置服务器(DEBUG=True)"
        python manage.py runserver 0.0.0.0:8000 --settings=CollectIp.settings.debug
        ;;
    4)
        echo "测试模式 - 运行测试套件"
        python manage.py test
        ;;
    *)
        echo "开发环境模式 - 使用Django内置服务器"
        python manage.py runserver 0.0.0.0:8000
        ;;
esac
fi 