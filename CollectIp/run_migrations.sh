#!/bin/bash
# 运行Django迁移脚本

echo "开始运行Django迁移..."

# 强制初始迁移
echo "创建初始迁移..."
python manage.py makemigrations --settings=CollectIp.settings_optimized

# 应用迁移
echo "应用迁移..."
python manage.py migrate --settings=CollectIp.settings_optimized

# 检查是否成功
if [ $? -ne 0 ]; then
  echo "错误：迁移失败。请检查错误信息。"
  exit 1
fi

echo "迁移完成。"
echo "是否创建超级用户？(y/n)"
read CREATE_SUPERUSER

if [[ "$CREATE_SUPERUSER" == "y" || "$CREATE_SUPERUSER" == "Y" ]]; then
  echo "创建超级用户..."
  python manage.py createsuperuser --settings=CollectIp.settings_optimized
fi

echo "收集静态文件..."
python manage.py collectstatic --settings=CollectIp.settings_optimized --noinput

echo "Django设置完成，现在可以配置Apache了。" 