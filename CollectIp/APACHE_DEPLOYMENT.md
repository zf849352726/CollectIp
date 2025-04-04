# CollectIp项目Apache部署指南（低内存优化版）

本指南将帮助您在Ubuntu服务器上使用Apache2和优化的设置部署CollectIp项目。这些配置针对低内存环境进行了优化。

## 1. 系统要求

- Ubuntu 20.04 LTS或更高版本
- 至少512MB内存（低内存环境）
- Python 3.8或更高版本
- Apache2与mod_wsgi
- MySQL 5.7或更高版本

## 2. 安装必要的软件包

```bash
# 更新系统
sudo apt update
sudo apt upgrade -y

# 安装Apache和相关软件包
sudo apt install -y apache2 libapache2-mod-wsgi-py3 python3-pip python3-dev python3-venv mysql-server

# 安装Python开发工具
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
```

## 3. 配置MySQL数据库

```bash
# 启动MySQL服务
sudo systemctl start mysql
sudo systemctl enable mysql

# 安全设置（根据提示操作）
sudo mysql_secure_installation

# 登录MySQL创建数据库
sudo mysql -u root -p
```

在MySQL提示符下执行以下命令：

```sql
CREATE DATABASE collectipdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'collectipuser'@'localhost' IDENTIFIED BY '您的密码';
GRANT ALL PRIVILEGES ON collectipdb.* TO 'collectipuser'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 4. 设置Python虚拟环境与项目

```bash
# 创建项目目录
sudo mkdir -p /var/www/collectip
sudo chown www-data:www-data /var/www/collectip

# 克隆项目（或上传您的项目）
cd /var/www
sudo -u www-data git clone [您的项目Git地址] collectip

# 创建并激活虚拟环境
cd /var/www/collectip
sudo -u www-data python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install mysqlclient gunicorn
```

## 5. 修改设置以使用优化的配置

编辑`settings_optimized.py`文件，更新数据库配置：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'collectipdb',
        'USER': 'collectipuser',  # 使用上面创建的用户
        'PASSWORD': '您的密码',    # 使用上面设置的密码
        'HOST': '127.0.0.1',
        'PORT': '3306',
        # 优化配置已包含
    },
    # ... MongoDB配置 ...
}
```

## 6. 收集静态文件与迁移数据库

```bash
# 确保您仍在虚拟环境中
# 收集静态文件
python manage.py collectstatic --settings=CollectIp.settings_optimized --noinput

# 创建数据库表
python manage.py migrate --settings=CollectIp.settings_optimized

# 创建超级用户（如需要）
python manage.py createsuperuser --settings=CollectIp.settings_optimized
```

## 7. 配置Apache

将项目中的`collectip_apache.conf`文件复制到Apache配置目录，并进行必要的修改：

```bash
sudo cp /var/www/collectip/collectip_apache.conf /etc/apache2/sites-available/collectip.conf
sudo nano /etc/apache2/sites-available/collectip.conf
```

修改配置文件中的路径，使其指向正确的位置：
- 将`/path/to/CollectIp`替换为`/var/www/collectip`
- 将`/path/to/venv`替换为`/var/www/collectip/venv`

配置文件示例：
```apache
<VirtualHost *:80>
    ServerAdmin webmaster@localhost
    DocumentRoot /var/www/collectip
    
    LogLevel warn
    ErrorLog ${APACHE_LOG_DIR}/collectip-error.log
    CustomLog ${APACHE_LOG_DIR}/collectip-access.log combined
    
    Alias /static/ /var/www/collectip/staticfiles/
    <Directory /var/www/collectip/staticfiles>
        Require all granted
        # 缓存配置...
    </Directory>
    
    Alias /media/ /var/www/collectip/media/
    <Directory /var/www/collectip/media>
        Require all granted
    </Directory>
    
    # 使用优化的WSGI文件
    WSGIScriptAlias / /var/www/collectip/CollectIp/wsgi_optimized.py
    
    WSGIDaemonProcess collectip python-home=/var/www/collectip/venv python-path=/var/www/collectip processes=1 threads=5 maximum-requests=500 inactivity-timeout=300
    WSGIProcessGroup collectip
    WSGIApplicationGroup %{GLOBAL}
    
    <Directory /var/www/collectip/CollectIp>
        <Files wsgi_optimized.py>
            Require all granted
        </Files>
    </Directory>
    
    # 压缩配置...
    
    # 设置环境变量
    SetEnv DJANGO_SETTINGS_MODULE CollectIp.settings_optimized
</VirtualHost>
```

## 8. 启用站点并配置Apache

```bash
# 启用必要的模块
sudo a2enmod wsgi expires deflate

# 启用站点
sudo a2ensite collectip.conf

# 禁用默认站点（可选）
sudo a2dissite 000-default.conf

# 检查配置是否有语法错误
sudo apache2ctl configtest

# 重启Apache
sudo systemctl restart apache2
```

## 9. 设置适当的权限

```bash
# 确保Apache可以访问项目文件
sudo chown -R www-data:www-data /var/www/collectip
sudo chmod -R 755 /var/www/collectip

# 确保logs目录存在并可写
sudo mkdir -p /var/www/collectip/logs
sudo chown -R www-data:www-data /var/www/collectip/logs
sudo chmod -R 755 /var/www/collectip/logs
```

## 10. 测试部署

在浏览器中访问您的服务器IP地址。如果一切配置正确，您应该能看到CollectIp项目的登录页面。

## 11. 内存优化建议

1. **监控Apache内存使用**
   ```bash
   sudo apt install htop
   htop
   ```

2. **优化MPM配置**
   编辑Apache MPM配置：
   ```bash
   sudo nano /etc/apache2/mods-available/mpm_prefork.conf
   ```
   
   使用以下优化设置：
   ```apache
   <IfModule mpm_prefork_module>
       StartServers             1
       MinSpareServers          1
       MaxSpareServers          3
       MaxRequestWorkers        10
       MaxConnectionsPerChild   1000
   </IfModule>
   ```

3. **启用内存限制工具**
   
   利用项目中的`run_with_memory_limit.py`脚本运行内存密集型任务：
   ```bash
   python run_with_memory_limit.py makemigrations
   python run_with_memory_limit.py migrate
   ```

## 12. 故障排查

1. **检查Apache错误日志**
   ```bash
   sudo tail -f /var/log/apache2/collectip-error.log
   ```

2. **验证WSGI配置**
   确保wsgi_optimized.py有正确的权限：
   ```bash
   sudo chmod 644 /var/www/collectip/CollectIp/wsgi_optimized.py
   ```

3. **检查静态文件访问**
   尝试在浏览器中访问静态文件，例如：
   ```
   http://your-server-ip/static/css/main.css
   ```

4. **验证环境变量设置**
   如果设置未应用，可在`wsgi_optimized.py`中直接设置环境变量。

## 13. 安全建议

1. **启用HTTPS**（如果可能）：
   ```bash
   sudo apt install certbot python3-certbot-apache
   sudo certbot --apache
   ```

2. **设置防火墙**：
   ```bash
   sudo apt install ufw
   sudo ufw allow 'Apache Full'
   sudo ufw allow 'OpenSSH'
   sudo ufw enable
   ```

3. **定期更新系统**：
   ```bash
   sudo apt update && sudo apt upgrade
   ``` 