#!/bin/bash
# CollectIp项目Apache部署脚本

# 设置颜色代码
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始CollectIp项目Apache部署...${NC}"

# 1. 检查静态文件目录
if [ ! -d "staticfiles" ]; then
  echo -e "${YELLOW}静态文件目录不存在，正在创建...${NC}"
  mkdir -p staticfiles
fi

# 2. 收集静态文件
echo -e "${GREEN}收集静态文件...${NC}"
python manage.py collectstatic --noinput

# 3. 设置Django数据库
echo -e "${GREEN}检查数据库迁移...${NC}"
python manage.py check
python manage.py migrate

# 4. 配置Apache
echo -e "${GREEN}准备Apache配置文件...${NC}"
if [ -f "collectip_apache.conf" ]; then
  echo -e "${GREEN}Apache配置文件已存在，复制到/etc/apache2/sites-available/${NC}"
  sudo cp collectip_apache.conf /etc/apache2/sites-available/
else
  echo -e "${RED}错误: collectip_apache.conf文件不存在${NC}"
  exit 1
fi

# 5. 启用Apache配置
echo -e "${GREEN}启用Apache配置...${NC}"
sudo a2enmod wsgi expires deflate
sudo a2ensite collectip.conf

# 6. 设置权限
echo -e "${GREEN}设置logs目录权限...${NC}"
mkdir -p logs
sudo chmod -R 755 logs

# 7. 重启Apache
echo -e "${GREEN}重启Apache...${NC}"
sudo systemctl restart apache2

# 8. 显示状态
echo -e "${GREEN}Apache状态:${NC}"
sudo systemctl status apache2

echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}现在您可以访问: http://您的服务器IP/${NC}"
echo -e "${YELLOW}如果遇到问题，请检查Apache错误日志:${NC}"
echo -e "${YELLOW}sudo tail -f /var/log/apache2/collectip-error.log${NC}" 