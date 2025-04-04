#!/bin/bash
# CollectIp项目完整部署脚本

# 设置颜色代码
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}    CollectIp项目Apache部署脚本（低内存环境）    ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 确保脚本在项目根目录运行
if [ ! -f "manage.py" ]; then
    echo -e "${RED}错误: 此脚本必须在项目根目录运行！${NC}"
    exit 1
fi

# Step 1: 准备数据库
echo -e "${GREEN}[Step 1/5] 准备数据库...${NC}"

# 检查数据库是否存在
echo -e "${YELLOW}检查数据库连接...${NC}"
DB_EXISTS=$(mysql -u root -p'Usb04usb.com' -e "SHOW DATABASES LIKE 'collectipdb';" 2>/dev/null | grep -o collectipdb)

if [ "$DB_EXISTS" != "collectipdb" ]; then
    echo -e "${YELLOW}创建数据库...${NC}"
    mysql -u root -p'Usb04usb.com' -e "CREATE DATABASE collectipdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}数据库创建失败。请检查MySQL连接和密码。${NC}"
        echo -e "${YELLOW}您可能需要手动创建数据库：${NC}"
        echo -e "CREATE DATABASE collectipdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        exit 1
    fi
    echo -e "${GREEN}数据库创建成功。${NC}"
else
    echo -e "${GREEN}数据库已存在，跳过创建步骤。${NC}"
fi

# Step 2: 执行数据库迁移
echo -e "${GREEN}[Step 2/5] 执行数据库迁移...${NC}"
python manage.py migrate --settings=CollectIp.settings_optimized

if [ $? -ne 0 ]; then
    echo -e "${RED}数据库迁移失败。请检查错误信息。${NC}"
    exit 1
fi
echo -e "${GREEN}数据库迁移成功。${NC}"

# Step 3: 收集静态文件
echo -e "${GREEN}[Step 3/5] 收集静态文件...${NC}"
python manage.py collectstatic --settings=CollectIp.settings_optimized --noinput

if [ $? -ne 0 ]; then
    echo -e "${RED}静态文件收集失败。请检查错误信息。${NC}"
    exit 1
fi
echo -e "${GREEN}静态文件收集成功。${NC}"

# Step 4: 配置Apache
echo -e "${GREEN}[Step 4/5] 配置Apache...${NC}"

# 检查collectip_apache.conf是否存在
if [ ! -f "collectip_apache.conf" ]; then
    echo -e "${RED}错误: collectip_apache.conf文件不存在！${NC}"
    exit 1
fi

echo -e "${YELLOW}复制Apache配置文件...${NC}"
sudo cp collectip_apache.conf /etc/apache2/sites-available/
sudo chmod 644 /etc/apache2/sites-available/collectip_apache.conf

echo -e "${YELLOW}启用必要的Apache模块...${NC}"
sudo a2enmod wsgi expires deflate

echo -e "${YELLOW}启用站点...${NC}"
sudo a2ensite collectip_apache.conf

echo -e "${YELLOW}检查Apache配置语法...${NC}"
sudo apache2ctl configtest

if [ $? -ne 0 ]; then
    echo -e "${RED}Apache配置检查失败。请修复配置错误。${NC}"
    exit 1
fi

# Step 5: 设置文件权限
echo -e "${GREEN}[Step 5/5] 设置文件权限...${NC}"

echo -e "${YELLOW}创建和设置logs目录权限...${NC}"
mkdir -p logs
sudo chmod -R 755 logs
sudo chown -R www-data:www-data logs

echo -e "${YELLOW}创建和设置media目录权限...${NC}"
mkdir -p media
sudo chmod -R 755 media
sudo chown -R www-data:www-data media

echo -e "${YELLOW}设置staticfiles目录权限...${NC}"
sudo chmod -R 755 staticfiles
sudo chown -R www-data:www-data staticfiles

echo -e "${YELLOW}设置wsgi.py文件权限...${NC}"
sudo chmod 644 CollectIp/wsgi.py

# 重启Apache
echo -e "${GREEN}重启Apache服务...${NC}"
sudo systemctl restart apache2

if [ $? -ne 0 ]; then
    echo -e "${RED}Apache重启失败。请检查系统日志获取更多信息。${NC}"
    echo -e "${YELLOW}您可以运行以下命令检查错误：${NC}"
    echo -e "sudo journalctl -xe"
    echo -e "sudo tail -f /var/log/apache2/error.log"
    exit 1
fi

# 询问是否创建超级用户
echo -e "${GREEN}是否要创建Django超级用户？(y/n)${NC}"
read CREATE_SUPERUSER

if [[ "$CREATE_SUPERUSER" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}创建Django超级用户...${NC}"
    python manage.py createsuperuser --settings=CollectIp.settings_optimized
fi

# 运行健康检查
echo -e "${GREEN}运行部署健康检查...${NC}"
python apache_health_check.py

echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}部署完成！您可以通过访问服务器IP或域名来查看网站。${NC}"
echo -e "${YELLOW}如需进一步排除故障，请查看Apache错误日志：${NC}"
echo -e "  sudo tail -f /var/log/apache2/collectip-error.log"
echo -e "${BLUE}====================================================${NC}" 