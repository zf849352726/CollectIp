#!/bin/bash
# Apache配置脚本

echo "开始配置Apache..."

# 确保mod_wsgi已安装
echo "检查mod_wsgi..."
if ! apache2ctl -M 2>/dev/null | grep -q "wsgi_module"; then
  echo "安装mod_wsgi..."
  sudo apt-get update
  sudo apt-get install -y libapache2-mod-wsgi-py3
  
  if [ $? -ne 0 ]; then
    echo "错误：mod_wsgi安装失败。"
    exit 1
  fi
fi

# 启用mod_wsgi
echo "启用mod_wsgi模块..."
sudo a2enmod wsgi
sudo a2enmod expires
sudo a2enmod deflate

# 复制Apache配置文件
echo "复制Apache配置文件..."
sudo cp collectip_apache.conf /etc/apache2/sites-available/

# 启用站点
echo "启用CollectIP站点..."
sudo a2ensite collectip_apache.conf

# 检查配置语法
echo "检查Apache配置语法..."
sudo apache2ctl configtest

if [ $? -ne 0 ]; then
  echo "错误：Apache配置存在语法错误。请检查collectip_apache.conf文件。"
  exit 1
fi

# 重启Apache
echo "重启Apache服务..."
sudo systemctl restart apache2

# 检查Apache状态
echo "检查Apache状态..."
sudo systemctl status apache2

echo "Apache配置完成。" 