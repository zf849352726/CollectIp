#!/bin/bash
# 验证MySQL连接脚本

echo "开始验证MySQL连接..."

# 测试MySQL连接
mysql -u root -p123456 -e "SELECT 'MySQL连接测试成功！' AS message;" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "MySQL连接成功！"
    
    # 验证数据库是否存在
    DB_EXISTS=$(mysql -u root -p123456 -e "SHOW DATABASES LIKE 'collectipdb';" 2>/dev/null | grep -o collectipdb)
    if [ "$DB_EXISTS" == "collectipdb" ]; then
        echo "数据库'collectipdb'存在。"
    else
        echo "警告：数据库'collectipdb'不存在！"
        echo "是否创建数据库？(y/n)"
        read CREATE_DB
        if [[ "$CREATE_DB" == "y" || "$CREATE_DB" == "Y" ]]; then
            mysql -u root -p123456 -e "CREATE DATABASE collectipdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            echo "数据库已创建。"
        fi
    fi
else
    echo "MySQL连接失败！请检查密码是否正确。"
fi

echo "检查完成。" 