# IP代理池系统

基于Django + Scrapy的IP代理池系统，支持自动采集、验证和评分。

## 主要功能

- 自动采集免费代理IP
- 验证码自动识别
- IP可用性验证和评分
- 代理池管理界面
- 定时任务调度

## 技术栈

- Django
- Scrapy
- Selenium
- ddddocr
- MySQL

## 安装使用

1. 克隆项目
```git clone https://github.com/你的用户名/项目名.git```

2. 安装依赖
```pip install -r requirements.txt```

3. 配置数据库
```python manage.py migrate```

4. 运行服务
```python manage.py runserver```

## 许可证

MIT
```