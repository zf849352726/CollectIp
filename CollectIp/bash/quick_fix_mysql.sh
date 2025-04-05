#!/bin/bash
# 快速修复MySQL连接问题的脚本

echo "===== 快速修复MySQL连接问题 ====="

# 更新Django设置文件中的MySQL密码
echo "更新Django设置文件中的数据库配置..."

# 备份Django设置文件
echo "备份Django设置文件..."
cp /usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py /usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py.bak

# 尝试更新密码（注意替换您之前执行过的 ALTER USER 命令中使用的密码）
echo "请输入正确的MySQL密码："
read -s MYSQL_PASSWORD

# 更新Django设置文件中的密码
sed -i "s/'PASSWORD': '.*'/'PASSWORD': '$MYSQL_PASSWORD'/" /usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py

echo "重启Apache..."
systemctl restart apache2

echo "修复完成！请尝试再次访问网站。" 