# CollectIp Linux 部署指南

本指南提供如何在内存有限的Linux VPS上部署和优化CollectIp项目的详细步骤。

## 系统要求

- Ubuntu 20.04 LTS或更高版本
- 至少512MB内存（推荐1GB以上）
- Python 3.8+
- MySQL 8.0+
- MongoDB 4.4+

## 内存优化措施

我们已经实施了多种内存优化措施，包括：

1. 优化的Django设置（`settings_optimized.py`）
2. 优化的Scrapy设置（`crawl_ip/settings_optimized.py`）
3. 内存受限的Gunicorn配置（`gunicorn_config.py`）
4. 内存优化的Nginx配置（`collectip_nginx.conf`）
5. Systemd服务配置以限制内存使用（`collectip.service`）
6. 用于限制Django命令内存使用的脚本（`run_with_memory_limit.py`）

## 部署步骤

### 1. 系统准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装依赖
sudo apt install -y python3 python3-venv python3-dev build-essential 
sudo apt install -y nginx mysql-server mongodb
sudo apt install -y libssl-dev libffi-dev libmysqlclient-dev
sudo apt install -y git supervisor 
```

### 2. 系统优化

```bash
# 增加交换空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo "/swapfile swap swap defaults 0 0" | sudo tee -a /etc/fstab

# 优化系统参数
echo "vm.swappiness=70" | sudo tee -a /etc/sysctl.conf
echo "vm.vfs_cache_pressure=200" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 3. 数据库配置

```bash
# 配置MySQL
sudo mysql_secure_installation
sudo mysql -e "CREATE DATABASE collectipdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER 'collectip'@'localhost' IDENTIFIED BY '123456';"
sudo mysql -e "GRANT ALL PRIVILEGES ON collectipdb.* TO 'collectip'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

# 优化MySQL配置
sudo cp /etc/mysql/mysql.conf.d/mysqld.cnf /etc/mysql/mysql.conf.d/mysqld.cnf.bak
sudo tee /etc/mysql/mysql.conf.d/mysqld.cnf.d/memory-optimized.cnf > /dev/null <<EOF
[mysqld]
# 内存优化设置
innodb_buffer_pool_size = 64M
innodb_log_buffer_size = 4M
max_connections = 50
key_buffer_size = 16M
table_open_cache = 400
sort_buffer_size = 256K
read_buffer_size = 256K
read_rnd_buffer_size = 256K
join_buffer_size = 256K
thread_cache_size = 8
query_cache_size = 8M
thread_stack = 192K
EOF

# 重启MySQL
sudo systemctl restart mysql
```

### 4. 克隆项目

```bash
# 创建应用目录
sudo mkdir -p /usr/local/CollectIp
sudo chown -R $USER:$USER /usr/local/CollectIp

# 克隆项目
git clone https://github.com/your-username/CollectIp.git /usr/local/CollectIp
cd /usr/local/CollectIp
```

### 5. 配置Python环境

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装优化的依赖
pip install --upgrade pip
pip install -r requirements-linux.txt

# 额外安装Gunicorn和Gevent
pip install gunicorn gevent
```

### 6. 配置项目

```bash
# 收集静态文件
DJANGO_SETTINGS_MODULE=CollectIp.settings_optimized python manage.py collectstatic --noinput

# 使用内存受限脚本运行迁移
chmod +x run_with_memory_limit.py
./run_with_memory_limit.py migrate
```

### 7. 配置Gunicorn

```bash
# 设置Gunicorn权限
sudo mkdir -p /usr/local/CollectIp/logs
sudo chown -R www-data:www-data /usr/local/CollectIp
```

### 8. 配置Nginx

```bash
# 创建Nginx配置
sudo cp collectip_nginx.conf /etc/nginx/sites-available/collectip
sudo ln -s /etc/nginx/sites-available/collectip /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

### 9. 配置Systemd服务

```bash
# 安装服务文件
sudo cp collectip.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable collectip
sudo systemctl start collectip
```

### 10. 设置防火墙（可选）

```bash
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 内存使用监控

```bash
# 安装监控工具
sudo apt install -y htop sysstat

# 监控内存使用
htop

# 查看系统日志
sudo journalctl -u collectip
```

## 故障排除

### 1. 如果遇到"Killed"问题

如果命令被系统终止并显示"Killed"，这通常是由于内存不足：

```bash
# 检查系统日志
sudo dmesg | grep -i "out of memory"

# 使用内存限制运行器
./run_with_memory_limit.py [命令]
```

### 2. MySQL启动失败

如果MySQL启动失败，可能是内存配置过高：

```bash
# 进一步降低MySQL内存使用
sudo tee /etc/mysql/mysql.conf.d/mysqld.cnf.d/tiny-memory.cnf > /dev/null <<EOF
[mysqld]
innodb_buffer_pool_size = 32M
innodb_log_buffer_size = 2M
max_connections = 25
EOF
sudo systemctl restart mysql
```

### 3. Django迁移故障

```bash
# 尝试逐个应用迁移
./run_with_memory_limit.py migrate auth
./run_with_memory_limit.py migrate sessions
./run_with_memory_limit.py migrate index
./run_with_memory_limit.py migrate ip_operator
```

## 性能优化提示

1. **定期重启服务**：配置定时任务，定期重启应用以释放内存。
2. **分批处理数据**：大型数据处理任务应分批进行。
3. **禁用不必要的功能**：根据需要禁用不必要的功能。
4. **使用异步任务**：将耗时任务移至异步处理。

## 结论

通过以上优化措施，CollectIp应用可以在内存有限的Linux VPS上稳定运行。如有任何问题，请查看应用日志和系统日志进行诊断。 