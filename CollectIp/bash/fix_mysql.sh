#!/bin/bash
# 修复MySQL连接问题脚本

# 设置颜色代码
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}    修复MySQL连接问题脚本    ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 测试MySQL连接
echo -e "${GREEN}测试MySQL连接...${NC}"
mysql -u root -p'Usb04usb.com' -e "SELECT 1" 2>/dev/null

if [ $? -ne 0 ]; then
    echo -e "${RED}MySQL连接失败！${NC}"
    echo -e "${YELLOW}可能的原因:${NC}"
    echo -e "1. MySQL密码不正确"
    echo -e "2. MySQL用户权限问题"
    echo -e "3. MySQL服务未运行"
    
    # 检查MySQL服务状态
    echo -e "\n${GREEN}检查MySQL服务状态...${NC}"
    systemctl status mysql | grep Active
    
    # 询问是否重置MySQL密码
    echo -e "\n${YELLOW}是否尝试修复MySQL密码？(y/n)${NC}"
    read fix_password
    
    if [[ "$fix_password" == "y" || "$fix_password" == "Y" ]]; then
        echo -e "${GREEN}请输入新的MySQL密码:${NC}"
        read -s NEW_PASSWORD
        echo -e "${GREEN}确认新的MySQL密码:${NC}"
        read -s CONFIRM_PASSWORD
        
        if [ "$NEW_PASSWORD" != "$CONFIRM_PASSWORD" ]; then
            echo -e "${RED}密码不匹配，请重新运行脚本。${NC}"
            exit 1
        fi
        
        # 备份Django设置文件
        echo -e "${GREEN}备份Django设置文件...${NC}"
        cp /usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py /usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py.bak
        
        # 修改MySQL root用户密码
        echo -e "${GREEN}尝试修改MySQL密码...${NC}"
        echo "请输入当前MySQL root密码（如果有的话）"
        mysqladmin -u root -p password "$NEW_PASSWORD"
        
        if [ $? -ne 0 ]; then
            echo -e "${YELLOW}尝试使用另一种方法修改密码...${NC}"
            echo "这将尝试使用sudo权限修改MySQL密码"
            
            # 停止MySQL服务
            sudo systemctl stop mysql
            
            # 以安全模式启动MySQL
            sudo mkdir -p /var/run/mysqld
            sudo chown mysql:mysql /var/run/mysqld
            sudo mysqld_safe --skip-grant-tables &
            sleep 5
            
            # 修改密码
            echo -e "${GREEN}更新root用户密码...${NC}"
            sudo mysql -e "USE mysql; UPDATE user SET authentication_string=PASSWORD('$NEW_PASSWORD') WHERE User='root'; FLUSH PRIVILEGES;"
            
            # 如果上面的命令不适用于较新版本的MySQL，尝试以下命令
            sudo mysql -e "USE mysql; ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$NEW_PASSWORD'; FLUSH PRIVILEGES;"
            
            # 停止安全模式MySQL
            sudo killall mysqld
            sleep 2
            
            # 重启MySQL服务
            sudo systemctl start mysql
        fi
        
        # 测试新密码
        echo -e "${GREEN}测试新密码...${NC}"
        mysql -u root -p"$NEW_PASSWORD" -e "SELECT 1"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}MySQL密码更新成功！${NC}"
            
            # 更新Django设置文件中的密码
            echo -e "${GREEN}更新Django设置文件中的数据库密码...${NC}"
            sed -i "s/'PASSWORD': '.*'/'PASSWORD': '$NEW_PASSWORD'/" /usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py
            
            echo -e "${GREEN}重启Apache...${NC}"
            sudo systemctl restart apache2
            
            echo -e "${GREEN}修复完成！请尝试再次访问网站。${NC}"
        else
            echo -e "${RED}修改密码失败。MySQL密码可能未更新。${NC}"
            echo -e "${YELLOW}请尝试手动修改MySQL密码：${NC}"
            echo -e "1. 停止MySQL: sudo systemctl stop mysql"
            echo -e "2. 安全模式启动: sudo mysqld_safe --skip-grant-tables &"
            echo -e "3. 连接MySQL: mysql -u root"
            echo -e "4. 运行: USE mysql; ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '新密码'; FLUSH PRIVILEGES;"
            echo -e "5. 重启MySQL: sudo systemctl restart mysql"
            
            # 恢复原始设置文件
            echo -e "${GREEN}恢复原始Django设置文件...${NC}"
            cp /usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py.bak /usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py
        fi
    else
        echo -e "${YELLOW}没有修改MySQL密码。请手动检查MySQL配置。${NC}"
    fi
else
    echo -e "${GREEN}MySQL连接成功！${NC}"
    echo -e "${YELLOW}但Django仍然无法连接，检查Django设置文件...${NC}"
    
    # 检查Django设置文件中的数据库配置
    echo -e "${GREEN}显示Django设置文件中的数据库配置...${NC}"
    grep -A 10 "DATABASES = {" /usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py
    
    # 询问是否要更新Django设置
    echo -e "\n${YELLOW}是否更新Django设置文件中的数据库配置？(y/n)${NC}"
    read update_settings
    
    if [[ "$update_settings" == "y" || "$update_settings" == "Y" ]]; then
        echo -e "${GREEN}请输入正确的MySQL密码:${NC}"
        read -s CORRECT_PASSWORD
        
        # 备份Django设置文件
        echo -e "${GREEN}备份Django设置文件...${NC}"
        cp /usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py /usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py.bak
        
        # 更新Django设置文件中的密码
        echo -e "${GREEN}更新Django设置文件中的数据库密码...${NC}"
        sed -i "s/'PASSWORD': '.*'/'PASSWORD': '$CORRECT_PASSWORD'/" /usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py
        
        echo -e "${GREEN}重启Apache...${NC}"
        sudo systemctl restart apache2
        
        echo -e "${GREEN}修复完成！请尝试再次访问网站。${NC}"
    else
        echo -e "${YELLOW}没有更新Django设置。请手动检查设置文件。${NC}"
    fi
fi

# 显示MySQL用户权限
echo -e "\n${GREEN}显示MySQL用户和权限信息...${NC}"
mysql -u root -p -e "SELECT user, host, plugin FROM mysql.user WHERE user='root';"

echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}脚本执行完成${NC}"
echo -e "${BLUE}====================================================${NC}" 