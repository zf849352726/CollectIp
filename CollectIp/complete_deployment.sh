#!/bin/bash
# 完整的CollectIp部署脚本

# 设置颜色代码
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}    CollectIp项目部署脚本 - 优化版   ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 确保当前目录正确
if [ ! -f "manage.py" ]; then
    echo -e "${RED}错误: 脚本必须在项目根目录运行！${NC}"
    exit 1
fi

# 第1步: 更新设置文件中的MySQL密码
echo -e "${GREEN}【步骤1/6】更新数据库设置...${NC}"
if grep -q "PASSWORD = 'Usb04usb.com'" CollectIp/settings_optimized.py; then
    echo -e "${GREEN}数据库密码已更新。${NC}"
else
    echo -e "${YELLOW}更新数据库密码...${NC}"
    sed -i "s/PASSWORD = '.*'/PASSWORD = 'Usb04usb.com'/" CollectIp/settings_optimized.py
    if [ $? -ne 0 ]; then
        echo -e "${RED}更新密码失败。请手动修改settings_optimized.py中的密码。${NC}"
        exit 1
    fi
    echo -e "${GREEN}数据库密码已更新。${NC}"
fi

# 第2步: 修复admin错误
echo -e "${GREEN}【步骤2/6】修复URL配置...${NC}"
if [ -f "CollectIp/urls_optimized.py" ]; then
    echo -e "${GREEN}优化版URL配置已存在。${NC}"
else
    echo -e "${YELLOW}创建优化版URL配置...${NC}"
    bash fix_admin_error.sh
    if [ $? -ne 0 ]; then
        echo -e "${RED}URL配置修复失败。请检查错误信息。${NC}"
        exit 1
    fi
    echo -e "${GREEN}URL配置已修复。${NC}"
fi

# 第3步: 初始化数据库
echo -e "${GREEN}【步骤3/6】初始化数据库...${NC}"
echo -e "${YELLOW}检查并创建数据库...${NC}"
mysql -u root -p'Usb04usb.com' -e "CREATE DATABASE IF NOT EXISTS collectipdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
if [ $? -ne 0 ]; then
    echo -e "${RED}数据库初始化失败。请检查MySQL连接和密码。${NC}"
    exit 1
fi
echo -e "${GREEN}数据库初始化成功。${NC}"

# 第4步: 运行迁移
echo -e "${GREEN}【步骤4/6】执行Django迁移...${NC}"
echo -e "${YELLOW}迁移核心应用...${NC}"
python manage.py migrate auth --settings=CollectIp.settings_optimized
python manage.py migrate contenttypes --settings=CollectIp.settings_optimized
python manage.py migrate sessions --settings=CollectIp.settings_optimized
echo -e "${YELLOW}迁移项目应用...${NC}"
python manage.py migrate index --settings=CollectIp.settings_optimized
python manage.py migrate ip_operator --settings=CollectIp.settings_optimized

# 第5步: 收集静态文件
echo -e "${GREEN}【步骤5/6】收集静态文件...${NC}"
python manage.py collectstatic --settings=CollectIp.settings_optimized --noinput
if [ $? -ne 0 ]; then
    echo -e "${RED}静态文件收集失败。请检查错误信息。${NC}"
    exit 1
fi
echo -e "${GREEN}静态文件收集成功。${NC}"

# 第6步: 配置Apache
echo -e "${GREEN}【步骤6/6】配置Apache...${NC}"

# 确保mod_wsgi已安装
echo -e "${YELLOW}检查Apache模块...${NC}"
if ! apache2ctl -M 2>/dev/null | grep -q "wsgi_module"; then
    echo -e "${YELLOW}安装mod_wsgi模块...${NC}"
    apt-get update && apt-get install -y libapache2-mod-wsgi-py3
    a2enmod wsgi
fi

# 启用必要的模块
echo -e "${YELLOW}启用必要的Apache模块...${NC}"
a2enmod wsgi expires deflate

# 复制并启用Apache配置
echo -e "${YELLOW}配置Apache...${NC}"
cp collectip_apache.conf /etc/apache2/sites-available/
chmod 644 /etc/apache2/sites-available/collectip_apache.conf
a2ensite collectip_apache.conf

# 设置必要的权限
echo -e "${YELLOW}设置文件权限...${NC}"
mkdir -p logs media staticfiles
chmod -R 755 logs media staticfiles
chown -R www-data:www-data logs media staticfiles
chmod 644 CollectIp/wsgi.py

# 检查Apache配置
echo -e "${YELLOW}检查Apache配置...${NC}"
apache2ctl configtest
if [ $? -ne 0 ]; then
    echo -e "${RED}Apache配置检查失败。请修复错误后重试。${NC}"
    exit 1
fi

# 重启Apache
echo -e "${YELLOW}重启Apache...${NC}"
systemctl restart apache2
if [ $? -ne 0 ]; then
    echo -e "${RED}Apache重启失败。请检查日志获取更多信息。${NC}"
    systemctl status apache2
    exit 1
fi

# 检查结果
echo -e "${GREEN}运行健康检查...${NC}"
python apache_health_check.py

echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${BLUE}====================================================${NC}"

echo -e "${YELLOW}您现在可以通过浏览器访问服务器来使用CollectIp。${NC}"
echo -e "${YELLOW}如果需要创建超级用户，请运行:${NC}"
echo -e "${GREEN}python manage.py createsuperuser --settings=CollectIp.settings_optimized${NC}" 