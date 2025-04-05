#!/bin/bash
# 启用CollectIp站点配置脚本

echo "开始配置Apache站点..."

# 检查配置文件
if [ ! -f "collectip_apache.conf" ]; then
    echo "错误: collectip_apache.conf文件不存在！"
    exit 1
fi

# 复制配置文件
echo "复制配置文件到Apache目录..."
sudo cp collectip_apache.conf /etc/apache2/sites-available/

# 启用站点
echo "禁用默认站点..."
sudo a2dissite 000-default.conf

echo "启用CollectIp站点..."
sudo a2ensite collectip_apache.conf

# 重新加载Apache配置
echo "重新加载Apache配置..."
sudo systemctl reload apache2

# 重启Apache
echo "重启Apache服务..."
sudo systemctl restart apache2

# 检查状态
echo "检查Apache状态..."
sudo systemctl status apache2

echo "配置完成，请访问您的服务器IP地址检查站点是否正常运行。" 