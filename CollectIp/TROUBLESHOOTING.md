# CollectIp项目部署问题排查指南

## 1. Apache错误："Invalid command 'WSGIScriptAlias'"

### 问题描述
Apache启动时显示错误：`Invalid command 'WSGIScriptAlias', perhaps misspelled or defined by a module not included in the server configuration`

### 解决方法
这个错误表明`mod_wsgi`模块未安装或未启用。

1. 安装mod_wsgi：
   ```bash
   sudo apt-get update
   sudo apt-get install -y libapache2-mod-wsgi-py3
   ```

2. 启用mod_wsgi：
   ```bash
   sudo a2enmod wsgi
   ```

3. 重启Apache：
   ```bash
   sudo systemctl restart apache2
   ```

## 2. 数据库迁移错误："Table 'collectipdb.django_migrations' doesn't exist"

### 问题描述
运行健康检查时显示错误：`错误: (1146, "Table 'collectipdb.django_migrations' doesn't exist")`

### 解决方法
这个错误表明数据库表尚未创建。

1. 确保数据库存在：
   ```bash
   mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS collectipdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   ```

2. 创建迁移文件：
   ```bash
   python manage.py makemigrations --settings=CollectIp.settings_optimized
   ```

3. 应用迁移：
   ```bash
   python manage.py migrate --settings=CollectIp.settings_optimized
   ```

## 3. Apache配置错误："No such file or directory"

### 问题描述
Apache启动时提示找不到文件或目录。

### 解决方法
1. 检查Apache配置中的路径是否正确，特别是：
   - `DocumentRoot`
   - `WSGIScriptAlias`
   - 静态文件和媒体文件的路径

2. 确保所有目录和文件都存在且具有正确的权限：
   ```bash
   # 检查wsgi.py文件
   ls -la /usr/local/CollectIp/CollectIp/CollectIp/wsgi.py
   
   # 设置正确的权限
   sudo chmod 644 /usr/local/CollectIp/CollectIp/CollectIp/wsgi.py
   ```

## 4. 数据库连接错误："Access denied for user"

### 问题描述
Django尝试连接数据库时返回"Access denied for user"错误。

### 解决方法
1. 检查MySQL用户名和密码是否正确：
   ```bash
   # 测试MySQL连接
   mysql -u root -p
   ```

2. 确保在`settings_optimized.py`中配置的数据库信息正确：
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'collectipdb',
           'USER': 'root',
           'PASSWORD': 'Usb04usb.com',  # 确保此密码正确
           'HOST': '127.0.0.1',
           'PORT': '3306',
       }
   }
   ```

## 5. 静态文件未加载

### 问题描述
部署后，网站的CSS、JavaScript和图片等静态文件无法正常加载。

### 解决方法
1. 确保已收集静态文件：
   ```bash
   python manage.py collectstatic --settings=CollectIp.settings_optimized --noinput
   ```

2. 检查Apache配置中的静态文件路径：
   ```apache
   Alias /static/ /usr/local/CollectIp/CollectIp/staticfiles/
   ```

3. 确保目录权限正确：
   ```bash
   sudo chmod -R 755 /usr/local/CollectIp/CollectIp/staticfiles
   sudo chown -R www-data:www-data /usr/local/CollectIp/CollectIp/staticfiles
   ```

## 6. 系统日志查看

当遇到问题时，检查以下日志文件可能会有帮助：

1. Apache错误日志：
   ```bash
   sudo tail -f /var/log/apache2/collectip-error.log
   ```

2. Apache访问日志：
   ```bash
   sudo tail -f /var/log/apache2/collectip-access.log
   ```

3. Django日志：
   ```bash
   tail -f /usr/local/CollectIp/CollectIp/logs/django.log
   ```

4. 系统日志：
   ```bash
   sudo journalctl -xe
   ```

## 7. Apache状态检查

检查Apache状态和语法：

```bash
# 检查Apache状态
sudo systemctl status apache2

# 检查Apache配置语法
sudo apache2ctl configtest

# 查看已加载的模块
sudo apache2ctl -M
```

## 8. Python环境问题

如果遇到Python相关错误：

1. 确认虚拟环境路径：
   ```bash
   # 在Apache配置中确认python-home路径正确
   WSGIDaemonProcess collectip python-home=/usr/local/venv/djangoLearn python-path=/usr/local/CollectIp/CollectIp
   ```

2. 检查Django是否已安装在虚拟环境中：
   ```bash
   source /usr/local/venv/djangoLearn/bin/activate
   pip list | grep Django
   ``` 