#!/bin/bash
# CollectIp项目主部署脚本

# 设置颜色代码
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}         CollectIp项目部署脚本         ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 检查是否在项目根目录
if [ ! -f "manage.py" ]; then
    echo -e "${RED}错误: 此脚本必须在项目根目录运行！${NC}"
    exit 1
fi

# 设置执行权限
echo -e "${YELLOW}设置脚本执行权限...${NC}"
chmod +x init_db_mysql.sh run_migrations.sh setup_apache.sh

# 第1步: 初始化MySQL数据库
echo -e "${GREEN}第1步: 初始化MySQL数据库${NC}"
./init_db_mysql.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}MySQL数据库初始化失败。请修复错误后重试。${NC}"
    exit 1
fi
echo -e "${GREEN}MySQL数据库初始化成功。${NC}"

# 第2步: 运行Django迁移
echo -e "${GREEN}第2步: 运行Django迁移${NC}"
./run_migrations.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}Django迁移失败。请修复错误后重试。${NC}"
    exit 1
fi
echo -e "${GREEN}Django迁移成功。${NC}"

# 第3步: 设置Apache
echo -e "${GREEN}第3步: 设置Apache${NC}"
./setup_apache.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}Apache配置失败。请修复错误后重试。${NC}"
    exit 1
fi
echo -e "${GREEN}Apache配置成功。${NC}"

# 第4步: 设置文件权限
echo -e "${GREEN}第4步: 设置文件权限${NC}"
echo -e "${YELLOW}设置目录权限...${NC}"

# 创建并设置logs目录权限
mkdir -p logs
sudo chmod -R 755 logs
sudo chown -R www-data:www-data logs

# 创建并设置media目录权限
mkdir -p media
sudo chmod -R 755 media
sudo chown -R www-data:www-data media

# 设置staticfiles目录权限
sudo chmod -R 755 staticfiles
sudo chown -R www-data:www-data staticfiles

# 设置wsgi.py文件权限
sudo chmod 644 CollectIp/wsgi.py

echo -e "${GREEN}文件权限设置完成。${NC}"

# 第5步: 检查部署状态
echo -e "${GREEN}第5步: 检查部署状态${NC}"
echo -e "${YELLOW}运行健康检查...${NC}"
python apache_health_check.py

echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}部署完成！您可以通过访问服务器IP或域名来验证部署是否成功。${NC}"
echo -e "${YELLOW}如果遇到问题，请检查Apache错误日志:${NC}"
echo -e "  sudo tail -f /var/log/apache2/collectip-error.log"
echo -e "${BLUE}====================================================${NC}" 