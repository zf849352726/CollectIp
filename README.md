# CollectIP

专注于代理 IP 的采集、管理、动态检测与对外服务。项目不包含电影、评论或其他爬虫业务。

## 功能

- Playwright + OCR 采集公开代理
- 已验证代理加权随机参与后续采集，并支持失败换线和直连兜底
- 与 Chromium 版本匹配的动态 UA、合理 viewport、请求节奏和指数退避
- HTTP/HTTPS 多检测源并发验证和出口 IP 校验
- 24 小时成功率、滚动延迟、稳定性综合评分
- 检测历史、错误分类、代理详情与历史图表
- 持久化任务队列、数据库互斥锁、独立 Worker
- 自动采集、自动评分、失败归档和过期清理
- Web 管理端和可供其他爬虫调用的 JSON API
- 管理操作登录保护、环境变量配置、轮转日志
- 管理员结构化运行日志、筛选查询和自动过期清理
- Windows、Docker 和 systemd 部署示例

## 初始化

```powershell
cd D:\CollectIP
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PLAYWRIGHT_BROWSERS_PATH="$PWD\.playwright-browsers"
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
```

复制 `.env.example` 为 `.env`。生产环境必须修改密钥、关闭 DEBUG，并仅在 HTTPS
反向代理已经配置完成后启用 `COLLECTIP_SECURE=true`。

## 运行

Web：

```powershell
.\scripts\start_web.ps1
```

独立 Worker（另一个终端）：

```powershell
.\scripts\start_worker.ps1
```

访问 `http://127.0.0.1:8000/`。列表和 API 可以匿名读取；采集、评分和设置修改需要管理员登录。
启动脚本会自动执行迁移和 `collectstatic`，静态资源由 WhiteNoise 随 Waitress
直接提供，不需要额外启动静态文件服务器。

## API

```text
GET /api/proxies/
GET /api/proxies/?available=true&min_score=80
GET /api/proxies/?https=true&country=China
GET /api/proxies/random/
GET /api/proxies/random/?https=true&min_score=70
GET /api/status/
GET /health/
```

列表支持 `status=available|unavailable|archived`、`q`、`min_score`、`https=true`、`page` 和 `page_size`。

## 任务与调度

Web 操作只创建数据库任务；`run_worker` 独立领取任务，因此 Web 重启不会丢任务，
同类任务不会重复入队。Worker 使用原子状态更新抢占任务，并自动释放超过两小时未完成的任务。

自动采集和评分可在 Web 设置中启用。Worker 根据数据库中的间隔自动创建任务。

采集任务默认从过去 24 小时内验证成功且评分不低于 60 的代理中加权随机
选择三条线路。线路失败后按指数退避切换，全部失败时回退直连。首次运行或
没有合格代理时也会使用直连，避免代理池无法自我恢复。所有采集尝试、验证码、
页面进度、换线和任务结果都会写入仅管理员可访问的 `/logs/`。
失败的自动任务会等待完整调度间隔后再尝试，避免快速失败循环；Windows Worker
启动脚本会先校验并补装与当前 Playwright 版本匹配的 Chromium。
项目内运行采集命令时会自动发现 `.playwright-browsers`，不需要在每个新终端
重复设置 `PLAYWRIGHT_BROWSERS_PATH`。

兼容命令：

```powershell
.\.venv\Scripts\python.exe manage.py collect_proxies --max-pages 2
.\.venv\Scripts\python.exe manage.py score_proxies
.\.venv\Scripts\python.exe manage.py monitor_proxies --once
```

## 评分规则

- 当前多目标成功率：50 分
- 延迟：30 分
- 连续稳定性：20 分
- 单次失败仅扣 10 分
- 达到配置的连续失败次数后归档
- 再次采集到同一代理时自动解除归档
- 归档超过保留天数后由 cleanup 任务删除

## 测试

```powershell
.\.venv\Scripts\python.exe manage.py test -v 2
ruff check --no-cache .
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

健康检查：`GET /health/`。
