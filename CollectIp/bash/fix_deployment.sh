#!/bin/bash
# 修复CollectIp部署的脚本

# 设置颜色代码
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}    CollectIp部署修复脚本   ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 检查当前目录
if [ ! -f "manage.py" ]; then
    echo -e "${RED}错误: 此脚本必须在项目根目录运行！${NC}"
    exit 1
fi

# 检查所需文件
echo -e "${GREEN}检查必要文件...${NC}"
if [ ! -f "collectip_apache.conf" ]; then
    echo -e "${RED}错误: collectip_apache.conf文件不存在！${NC}"
    exit 1
fi

if [ ! -f "CollectIp/wsgi.py" ]; then
    echo -e "${RED}错误: wsgi.py文件不存在！${NC}"
    exit 1
fi

# 检查mod_wsgi模块
echo -e "${GREEN}检查Apache模块...${NC}"
if ! apache2ctl -M 2>/dev/null | grep -q "wsgi_module"; then
    echo -e "${YELLOW}mod_wsgi模块未加载，正在安装...${NC}"
    sudo apt-get update && sudo apt-get install -y libapache2-mod-wsgi-py3
    sudo a2enmod wsgi
    if [ $? -ne 0 ]; then
        echo -e "${RED}mod_wsgi安装失败！${NC}"
        exit 1
    fi
fi

# 复制配置文件
echo -e "${GREEN}更新Apache配置...${NC}"
sudo cp collectip_apache.conf /etc/apache2/sites-available/
sudo chmod 644 /etc/apache2/sites-available/collectip_apache.conf

# 禁用默认站点，启用CollectIp站点
echo -e "${YELLOW}禁用默认站点...${NC}"
sudo a2dissite 000-default.conf
echo -e "${YELLOW}启用CollectIp站点...${NC}"
sudo a2ensite collectip_apache.conf

# 启用必要的模块
echo -e "${YELLOW}启用Apache模块...${NC}"
sudo a2enmod wsgi expires deflate

# 设置文件和目录权限
echo -e "${GREEN}设置文件权限...${NC}"
sudo mkdir -p /usr/local/CollectIp/CollectIp/logs
sudo mkdir -p /usr/local/CollectIp/CollectIp/media
sudo mkdir -p /usr/local/CollectIp/CollectIp/staticfiles

sudo chmod -R 755 /usr/local/CollectIp/CollectIp/logs
sudo chmod -R 755 /usr/local/CollectIp/CollectIp/media
sudo chmod -R 755 /usr/local/CollectIp/CollectIp/staticfiles
sudo chmod 644 /usr/local/CollectIp/CollectIp/CollectIp/wsgi.py

sudo chown -R www-data:www-data /usr/local/CollectIp/CollectIp/logs
sudo chown -R www-data:www-data /usr/local/CollectIp/CollectIp/media
sudo chown -R www-data:www-data /usr/local/CollectIp/CollectIp/staticfiles

# 检查目录结构
echo -e "${GREEN}检查项目目录结构...${NC}"
echo -e "${YELLOW}项目目录:${NC}"
ls -la /usr/local/CollectIp/CollectIp/
echo -e "\n${YELLOW}CollectIp目录:${NC}"
ls -la /usr/local/CollectIp/CollectIp/CollectIp/

# 收集静态文件
echo -e "${GREEN}收集静态文件...${NC}"
python manage.py collectstatic --settings=CollectIp.settings_optimized --noinput

# 重新加载Apache配置
echo -e "${GREEN}重启Apache...${NC}"
sudo systemctl daemon-reload
sudo systemctl restart apache2

# 查看Apache状态
echo -e "${GREEN}检查Apache状态...${NC}"
sudo systemctl status apache2

# 查看日志
echo -e "${GREEN}检查Apache错误日志(最后10行)...${NC}"
sudo tail -n 10 /var/log/apache2/collectip-error.log

echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}修复脚本执行完成！${NC}"
echo -e "${YELLOW}现在请访问服务器IP地址查看网站是否正常运行。${NC}"
echo -e "${YELLOW}如果仍有问题，请检查日志文件：${NC}"
echo -e "Apache错误日志: ${GREEN}sudo tail -f /var/log/apache2/collectip-error.log${NC}"
echo -e "Django日志: ${GREEN}tail -f /usr/local/CollectIp/CollectIp/logs/django.log${NC}"
echo -e "${BLUE}====================================================${NC}" 