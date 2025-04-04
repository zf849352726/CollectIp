# CollectIp项目Apache部署指南（低内存环境）

本指南帮助您在低内存Ubuntu服务器上使用Apache2部署CollectIp项目。

## 1. 环境准备

确保您的系统已安装必要的软件包：

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要的软件包
sudo apt install -y apache2 libapache2-mod-wsgi-py3 python3-pip python3-dev python3-venv
sudo apt install -y mysql-server
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev pkg-config libmysqlclient-dev
```

## 2. 数据库准备

### 2.1 配置MySQL

如果尚未配置MySQL，您需要设置root密码并创建数据库：

```bash
# 运行MySQL安全配置
sudo mysql_secure_installation

# 对于MySQL 8.0，您可能需要修改认证方式
sudo mysql -u root -p
```

在MySQL提示符中执行：
```sql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '您的密码';
FLUSH PRIVILEGES;
CREATE DATABASE collectipdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

### 2.2 执行数据库迁移

```bash
# 确保脚本有执行权限
chmod +x migrate_db.sh
# 运行迁移脚本
./migrate_db.sh
```

## 3. 静态文件与Apache配置

### 3.1 收集静态文件

```bash
# 使用优化的设置收集静态文件
python manage.py collectstatic --settings=CollectIp.settings_optimized --noinput
```

### 3.2 配置Apache

```bash
# 复制Apache配置文件
sudo cp collectip_apache.conf /etc/apache2/sites-available/

# 启用必要的模块
sudo a2enmod wsgi expires deflate

# 启用站点
sudo a2ensite collectip.conf

# 禁用默认站点（可选）
sudo a2dissite 000-default.conf

# 检查配置语法
sudo apache2ctl configtest

# 重启Apache
sudo systemctl restart apache2
```

## 4. 设置文件权限

确保Apache能够访问项目文件：

```bash
# 确保logs目录存在并可写
mkdir -p logs
sudo chmod -R 755 logs

# 确保media目录存在并可写
mkdir -p media
sudo chmod -R 755 media

# 确保wsgi.py文件有正确的权限
sudo chmod 644 CollectIp/wsgi.py
```

## 5. 验证部署

完成所有步骤后，再次运行健康检查脚本：

```bash
python apache_health_check.py
```

如果所有检查都通过，您可以通过访问服务器IP或域名来验证部署是否成功。

## 6. 故障排查

### 6.1 数据库连接问题

如果遇到"Access denied"错误，请检查：
- MySQL服务是否正在运行
- 数据库用户名和密码是否正确
- 数据库是否存在

### 6.2 Apache错误

检查Apache错误日志：
```bash
sudo tail -f /var/log/apache2/collectip-error.log
```

### 6.3 静态文件问题

如果静态文件未正确加载：
- 确认staticfiles目录是否存在并包含文件
- 检查Apache配置中的静态文件路径是否正确

### 6.4 内存不足问题

如果服务器内存非常有限：
- 禁用不必要的Apache模块
- 减少WSGIDaemonProcess的进程数和线程数
- 考虑增加交换空间：
  ```bash
  sudo fallocate -l 1G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  ```

## 7. 安全建议

1. 在生产环境中保持DEBUG=False
2. 定期更新系统和依赖包
3. 考虑配置HTTPS
4. 限制数据库用户权限 