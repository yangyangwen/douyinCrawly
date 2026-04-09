# HTTP API

本文档面向 Web 服务 / Docker 部署场景，说明如何通过 HTTP 调用当前项目。

## 基本说明

- 默认服务地址：`http://localhost:8000`
- 大多数采集能力都依赖有效的抖音 `cookie`
- 如果配置了 `DOUYIN_API_AUTH_TOKEN`，所有 `/api` 请求都需要带 `Authorization: Bearer <token>`
- 推荐先调用 `POST /api/settings` 写入 `cookie` 和 `userAgent`
- `POST /api/settings` 是热更新，新任务直接生效，不需要重启进程
- 如果你手动改 `config/settings.json`，运行中的服务不会自动热加载

## 统一错误结构

当接口返回非 `2xx` 时，错误体统一为：

```json
{
  "error": {
    "code": "COOKIE_INVALID",
    "message": "Cookie 无效或已过期",
    "details": {
      "field": "keyword"
    }
  }
}
```

说明：

- `error.code`: 稳定错误码，适合程序判断
- `error.message`: 给人看的错误描述
- `error.details`: 可选，补充字段名、`task_id`、校验失败列表等上下文

当前已明确的常用错误码：

- `VALIDATION_ERROR`: 请求体或查询参数未通过校验
- `INVALID_REQUEST`: 业务层参数非法
- `CONFIG_INVALID`: 配置保存失败或配置值不合法
- `COOKIE_INVALID`: Cookie 缺失、格式错误或已失效
- `TASK_NOT_FOUND`: 查询了不存在的任务结果
- `RESOURCE_NOT_FOUND`: 通用资源不存在
- `INTERNAL_ERROR`: 服务内部异常

## 1. 健康检查

### `GET /api`

返回服务基本信息。

```bash
curl http://localhost:8000/api
```

### `GET /api/health`

返回服务就绪状态、Aria2 连接状态和配置是否已就绪。

```bash
curl http://localhost:8000/api/health
```

## 2. 配置管理

### `GET /api/settings`

读取当前运行中的配置。

```bash
curl http://localhost:8000/api/settings
```

### `POST /api/settings`

在线更新配置。常用场景是更新 `cookie`、`userAgent`、下载目录、并发参数。

```bash
curl -X POST http://localhost:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "cookie": "sessionid=xxx; ttwid=xxx",
    "userAgent": "Mozilla/5.0 ...",
    "maxRetries": 3,
    "maxConcurrency": 5
  }'
```

说明：

- 这是部分更新接口，只传需要修改的字段即可
- 更新后新的任务会直接读取最新配置
- Docker 场景也可以在启动时通过 `DOUYIN_COOKIE`、`DOUYIN_USER_AGENT` 环境变量覆盖

### `GET /api/settings/first-run`

判断是否首次运行。

```bash
curl http://localhost:8000/api/settings/first-run
```

## 3. 同步接口

### `POST /api/aweme/detail`

适合“给外部系统直接返回单条作品详情”的场景，不需要先创建任务再轮询。

```bash
curl -X POST http://localhost:8000/api/aweme/detail \
  -H "Content-Type: application/json" \
  -d '{
    "target": "https://www.douyin.com/video/7623004560194602874",
    "include_raw": false
  }'
```

请求字段：

- `target`: 作品 URL 或纯 aweme_id
- `include_raw`: 是否附带上游原始详情数据

响应重点字段：

- `aweme_id`: 作品 ID
- `resolved_url`: 规范化后的作品链接
- `content_type`: `video` / `image`
- `metrics.liked_count`: 点赞数
- `metrics.comment_count`: 评论数
- `metrics.collect_count`: 收藏数
- `metrics.share_count`: 分享数
- `item`: 当前解析后的完整详情对象

常见错误：

- `COOKIE_INVALID`: 当前运行配置里没有有效 Cookie
- `INVALID_REQUEST`: `target` 缺失或格式明显错误
- `RESOURCE_NOT_FOUND`: 作品不存在，或当前 Cookie 无法查看该作品

### `POST /api/search`

适合“给外部系统直接返回结果”的场景，不需要先创建任务再轮询。

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "美食",
    "limit": 18,
    "filters": {
      "sort_type": "2",
      "publish_time": "7",
      "filter_duration": "0-1"
    },
    "include_raw": false
  }'
```

请求字段：

- `keyword`: 搜索关键词
- `limit`: 返回数量上限，范围 `1-200`
- `filters.sort_type`: `0=综合`、`1=最多点赞`、`2=最新`
- `filters.publish_time`: `0=不限`、`1=一天内`、`7=一周内`、`180=半年内`
- `filters.filter_duration`: `0-1`、`1-5`、`5-10000`
- `include_raw`: 是否附带上游原始数据

常见错误：

- `COOKIE_INVALID`: 当前运行配置里没有有效 Cookie
- `VALIDATION_ERROR`: `keyword` 缺失，或 `limit` 超出 `1-200`

## 4. 异步任务接口

### `POST /api/task/start`

创建采集任务，适合耗时更长的采集流程。

```bash
curl -X POST http://localhost:8000/api/task/start \
  -H "Content-Type: application/json" \
  -d '{
    "type": "favorite",
    "target": "https://www.douyin.com/user/MS4wLjABxxx",
    "limit": 20
  }'
```

常见 `type`：

- `post`
- `favorite`
- `collection`
- `hashtag`
- `mix`
- `music`
- `search`
- `aweme`
- `following`
- `follower`

### `GET /api/task/status`

查询任务状态。

```bash
curl http://localhost:8000/api/task/status
curl "http://localhost:8000/api/task/status?task_id=task_xxx"
```

### `GET /api/task/results/{task_id}`

读取任务结果。

```bash
curl http://localhost:8000/api/task/results/task_xxx
```

如果任务不存在，会返回 `TASK_NOT_FOUND`。

### `GET /api/events`

SSE 事件流。前端界面就是通过它接收实时日志、任务状态和结果推送。

```bash
curl -N http://localhost:8000/api/events
```

## 5. Aria2 相关接口

### `GET /api/aria2/config`

返回当前 Aria2 连接配置。

### `GET /api/aria2/status`

返回当前 Aria2 是否连通。

### `POST /api/aria2/start`

尝试启动 Aria2。

### `GET /api/aria2/config-path`

读取当前任务关联的 `aria2.conf` 路径。

## 6. 其他接口

- `POST /api/system/cookie-login`: GUI 模式下打开抖音登录窗口并自动抓取 Cookie
- `GET /api/system/clipboard`: 读取系统剪贴板
- `POST /api/file/open-folder`: 打开本地目录
- `GET /api/file/media/{file_path}`: 读取已下载的媒体文件

## 部署提醒

- 当前接口默认没有鉴权，直接暴露公网前至少要补反向代理、访问控制、限流
- 当前 CORS 为 `*`，适合本地调试，不适合直接裸露到公网
- 当前任务状态和结果保存在内存中，服务重启后不会保留
- Docker 部署时建议挂载 `./config` 和 `./download`，项目根目录已自带 `compose.yaml`
