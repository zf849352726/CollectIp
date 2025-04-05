# 为663712.xyz配置SSL证书

本文档介绍如何为CollectIp应用程序配置SSL证书，使其能够通过HTTPS安全地访问。

## 准备工作

1. 确保您拥有域名`663712.xyz`的控制权。
2. 确保服务器可以从公网访问，使Let's Encrypt能够进行验证。
3. 确保您已安装Apache。

## 安装Certbot

Certbot是Let's Encrypt的官方客户端，可以帮助我们自动获取和更新SSL证书。

### 在Ubuntu/Debian上安装

```bash
sudo apt update
sudo apt install certbot python3-certbot-apache
```

### 在CentOS/RHEL上安装

```bash
sudo yum install epel-release
sudo yum install certbot python3-certbot-apache
```

## 获取SSL证书

使用Certbot为您的域名获取SSL证书：

```bash
sudo certbot --apache -d 663712.xyz -d www.663712.xyz
```

按照提示操作，Certbot会自动验证您对域名的控制权，并创建SSL证书，同时为您的Apache配置适当的设置。

## 手动配置Apache

如果您希望手动配置Apache，可以使用预先准备好的配置文件：

1. 确保启用了SSL模块：

```bash
sudo a2enmod ssl
sudo a2enmod headers
sudo a2enmod rewrite
```

2. 安装SSL证书：

```bash
sudo certbot certonly --webroot -w /usr/local/CollectIp/CollectIp -d 663712.xyz -d www.663712.xyz
```

3. 启用SSL配置：

```bash
sudo cp /usr/local/CollectIp/collectip_apache_ssl.conf /etc/apache2/sites-available/
sudo a2ensite collectip_apache_ssl.conf
```

4. 测试并重启Apache：

```bash
sudo apache2ctl configtest
sudo systemctl restart apache2
```

## 证书更新

Let's Encrypt证书有效期为90天，所以需要定期更新。Certbot会自动安装一个定时任务，每天检查证书是否需要更新。您可以手动检查：

```bash
sudo certbot renew --dry-run
```

## SSL配置检查

使用在线工具检查您的SSL配置安全性：

1. [SSL Labs](https://www.ssllabs.com/ssltest/)
2. [Security Headers](https://securityheaders.com/)

## 常见问题

### SSL证书续期失败

确保以下条件满足：
- 服务器可以从公网访问
- Certbot可以访问证书验证目录
- Apache配置没有错误

### HTTP到HTTPS重定向不工作

检查Apache是否启用了rewrite模块：

```bash
sudo a2enmod rewrite
sudo systemctl restart apache2
```

### 浏览器提示证书不受信任

确保您的证书链完整，包含了中间证书。使用`fullchain.pem`而不是`cert.pem`。
