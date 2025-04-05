#!/bin/bash
# 数据库迁移脚本

echo "开始执行数据库迁移..."

# 使用优化的设置执行迁移
echo "执行初始迁移..."
python manage.py migrate --settings=CollectIp.settings_optimized

# 检查迁移是否成功
if [ $? -eq 0 ]; then
  echo "迁移成功完成！"
else
  echo "迁移失败，请检查数据库连接设置。"
  exit 1
fi

echo "数据库迁移已完成，请再次运行健康检查。" 