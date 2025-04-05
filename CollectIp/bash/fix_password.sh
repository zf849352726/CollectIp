#!/bin/bash
# 重启Apache服务以应用新的MySQL密码

echo "密码已修改为123456，正在重启Apache服务..."
systemctl restart apache2

echo "操作完成，请尝试再次访问网站。" 