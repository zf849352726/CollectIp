# IP池打分系统

这是一个自动化的IP池打分系统，用于评估IP池中代理IP的质量。

## 功能特点

- 从MySQL数据库获取IP池数据
- 对IP进行并发测试和打分
- 自动更新IP分数到数据库
- 支持多个测试目标网站
- 具有完善的错误处理和日志记录

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

1. 创建`.env`文件，配置数据库连接信息：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=ip_pool
```

2. 确保数据库中存在`ip_pool`表，表结构如下：

```sql
CREATE TABLE ip_pool (
    id bigint NOT NULL AUTO_INCREMENT PRIMARY KEY,
    server varchar(21) NOT NULL UNIQUE,
    ping decimal(6,4),
    speed decimal(7,2),
    uptime1 varchar(5) NOT NULL,
    uptime2 varchar(5) NOT NULL,
    type_data varchar(20) NOT NULL,
    country varchar(20) NOT NULL,
    ssl varchar(50) NOT NULL,
    conn varchar(50) NOT NULL,
    post varchar(50) NOT NULL,
    last_work_time varchar(30) NOT NULL,
    score int NOT NULL
);
```

## 运行方式

```bash
python main.py
```

## 打分规则

- 系统会对每个IP测试多个目标网站
- 根据响应时间和成功率计算分数
- 分数范围：0-100分
- 默认每小时进行一次完整的打分循环 