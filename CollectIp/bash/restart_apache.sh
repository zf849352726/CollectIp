#!/bin/bash

# 脚本名称: restart_apache.sh
# 功能: 安全地重启Apache服务
# 作者: 系统管理员
# 日期: 2025-04-05

echo "======================================================"
echo "          Apache服务重启脚本 - CollectIp项目          "
echo "======================================================"

# 激活虚拟环境
echo "正在激活虚拟环境..."
if [ -f "/usr/local/venv/djangoLearn/bin/activate" ]; then
    source /usr/local/venv/djangoLearn/bin/activate
    echo "虚拟环境已激活"
else
    echo "警告: 虚拟环境文件不存在，继续执行但可能会有问题"
fi

# 检查Apache配置文件语法
echo "正在检查Apache配置文件语法..."
if sudo apache2ctl configtest; then
    echo "Apache配置检查通过!"
else
    echo "错误: Apache配置文件存在问题!"
    echo "是否仍要继续重启Apache? (y/n)"
    read -r confirm
    if [ "$confirm" != "y" ]; then
        echo "操作已取消"
        exit 1
    fi
    echo "警告: 尽管存在配置问题，但将继续重启Apache!"
fi

# 收集静态文件
echo "正在收集静态文件..."
cd "$(dirname "$0")/../.."
python manage.py collectstatic --noinput

# 检查Django项目
echo "检查Django项目状态..."
python manage.py check --deploy

# 重启Apache服务
echo "正在重启Apache服务..."
if sudo systemctl restart apache2; then
    echo "Apache服务已成功重启!"
else
    echo "错误: Apache服务重启失败!"
    exit 1
fi

# 检查Apache状态
echo "检查Apache服务状态..."
sudo systemctl status apache2

echo "======================================================"
echo "Apache服务重启完成，现在检查网站是否正常访问"
echo "您可以使用以下命令查看Apache日志:"
echo "sudo tail -f /var/log/apache2/error.log"
echo "======================================================" 