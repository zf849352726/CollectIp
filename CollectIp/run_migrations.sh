#!/bin/bash
# 运行Django迁移脚本

echo "开始运行Django迁移..."

# 确保数据库表存在
echo "强制初始迁移..."
python manage.py migrate auth --settings=CollectIp.settings_optimized
python manage.py migrate contenttypes --settings=CollectIp.settings_optimized
python manage.py migrate sessions --settings=CollectIp.settings_optimized
python manage.py migrate index --settings=CollectIp.settings_optimized
python manage.py migrate ip_operator --settings=CollectIp.settings_optimized

# 检查是否成功
if [ $? -ne 0 ]; then
  echo "警告：某些迁移可能未完成。尝试继续..."
fi

echo "创建应用迁移..."
# 对各个应用单独创建迁移，避免URL导入错误
python manage.py makemigrations index --settings=CollectIp.settings_optimized
python manage.py makemigrations ip_operator --settings=CollectIp.settings_optimized

# 应用迁移（按顺序）
echo "应用所有迁移..."
python manage.py migrate --settings=CollectIp.settings_optimized --run-syncdb

# 检查最终迁移结果
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