#!/bin/bash

# 脚本名称: activate_venv.sh
# 功能: 激活Django虚拟环境
# 作者: 系统管理员
# 日期: 2025-04-05

# 输出信息
echo "正在激活Django虚拟环境..."

# 获取当前目录
CURRENT_DIR=$(pwd)
echo "当前工作目录: $CURRENT_DIR"

# 激活虚拟环境
if [ -f "/usr/local/venv/djangoLearn/bin/activate" ]; then
    source /usr/local/venv/djangoLearn/bin/activate
    
    # 判断是否成功激活
    if [ $? -eq 0 ]; then
        echo "虚拟环境已成功激活!"
        echo "Python路径: $(which python)"
        echo "Python版本: $(python --version)"
        echo "虚拟环境目录: $VIRTUAL_ENV"
    else
        echo "虚拟环境激活失败!"
        exit 1
    fi
else
    echo "错误: 虚拟环境文件不存在!"
    echo "请检查路径: /usr/local/venv/djangoLearn/bin/activate"
    exit 1
fi

# 检查Django是否已安装
if python -c "import django; print(f'Django版本: {django.__version__}')" 2>/dev/null; then
    echo "Django安装检查通过"
else
    echo "警告: Django可能未安装或无法导入"
    echo "请使用 pip install django 进行安装"
fi

echo "环境准备就绪，可以运行Django项目"

# 设置提示符，表明已在虚拟环境中
PS1="(djangoLearn) $PS1" 