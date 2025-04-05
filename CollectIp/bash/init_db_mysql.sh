#!/bin/bash
# MySQL数据库初始化脚本

echo "开始初始化MySQL数据库..."

# MySQL密码
MYSQL_PASSWORD="Usb04usb.com"

# 确保collectipdb数据库存在
echo "创建数据库（如果不存在）..."
mysql -u root -p$MYSQL_PASSWORD -e "CREATE DATABASE IF NOT EXISTS collectipdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 检查是否成功
if [ $? -ne 0 ]; then
  echo "错误：数据库创建失败。请检查MySQL连接和密码。"
  exit 1
fi

echo "数据库初始化完成。"
echo "现在可以执行Django迁移了。" 