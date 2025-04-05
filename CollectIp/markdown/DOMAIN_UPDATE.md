# 迁移到新域名 663712.xyz 步骤

以下是将 CollectIp 项目迁移到新域名 663712.xyz 的简要步骤：

## 1. 更新配置文件

已经完成的配置文件更新：

- `CollectIp/settings.py` - 添加新域名到ALLOWED_HOSTS和CSRF_TRUSTED_ORIGINS
- `CollectIp/settings_optimized.py` - 同上，并启用生产环境安全设置
- `collectip_apache.conf` - 更新HTTP虚拟主机配置，添加HTTPS重定向
- `collectip_apache_ssl.conf` - 创建HTTPS虚拟主机配置

## 2. 域名解析设置

1. 在域名注册商处添加以下DNS记录：
   - A记录：将 `663712.xyz` 指向您的服务器IP
   - A记录：将 `www.663712.xyz` 指向您的服务器IP
   - CNAME记录：将 `www` 指向 `663712.xyz`（如果A记录不想重复配置）

2. 等待DNS生效（通常需要几分钟到几小时）。

## 3. 安装SSL证书

按照 `SSL_SETUP.md` 中的步骤安装SSL证书：

```bash
# 安装certbot
sudo apt update
sudo apt install certbot python3-certbot-apache

# 获取SSL证书
sudo certbot --apache -d 663712.xyz -d www.663712.xyz
```

或者手动配置：

```bash
# 启用必要的Apache模块
sudo a2enmod ssl
sudo a2enmod headers
sudo a2enmod rewrite

# 获取证书
sudo certbot certonly --webroot -w /usr/local/CollectIp/CollectIp -d 663712.xyz -d www.663712.xyz

# 复制SSL配置文件
sudo cp /usr/local/CollectIp/collectip_apache_ssl.conf /etc/apache2/sites-available/

# 启用站点
sudo a2ensite collectip_apache_ssl.conf

# 检查配置并重启Apache
sudo apache2ctl configtest
sudo systemctl restart apache2
```

## 4. 更新环境变量和邮件设置

更新 `/usr/local/CollectIp/CollectIp/.env` 文件（如果存在）：

```
# 邮件设置
EMAIL_HOST_USER=admin@663712.xyz
EMAIL_HOST_PASSWORD=your_actual_password
```

## 5. 测试

1. 验证HTTP到HTTPS重定向：
   - 访问 http://663712.xyz 应自动重定向到 https://663712.xyz

2. 验证HTTPS工作正常：
   - 访问 https://663712.xyz
   - 检查浏览器中的SSL锁图标是否显示安全连接

3. 测试各项功能是否正常：
   - 用户登录
   - 爬虫功能
   - 管理面板

## 6. 监控和故障排除

- 检查Apache错误日志：
  ```bash
  sudo tail -f /var/log/apache2/collectip-ssl-error.log
  ```

- 检查Django错误日志：
  ```bash
  sudo tail -f /usr/local/CollectIp/CollectIp/logs/django.log
  ```

- 如果遇到问题，参考 `TROUBLESHOOTING.md` 文件排查常见问题。 