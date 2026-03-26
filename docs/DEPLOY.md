# Docker 部署

## 1. 准备服务器

- 安装 Docker
- 安装 Docker Compose Plugin
- 开放服务器端口，默认是 `8000`
- 如果要对外提供服务，建议再配 Nginx / Caddy 反向代理

## 2. 准备环境变量

在项目根目录创建 `.env`：

```env
DOUYIN_HOST=0.0.0.0
DOUYIN_PORT=8000
DOUYIN_COOKIE=你的抖音 Cookie
DOUYIN_USER_AGENT=与 Cookie 对应的 User-Agent
DOUYIN_MAX_RETRIES=3
DOUYIN_MAX_CONCURRENCY=5
DOUYIN_ENABLE_INCREMENTAL_FETCH=true
DOUYIN_ARIA2_HOST=localhost
DOUYIN_ARIA2_PORT=6800
DOUYIN_ARIA2_SECRET=自行修改一个复杂值
```

说明：

- `DOUYIN_COOKIE` 和 `DOUYIN_USER_AGENT` 会在容器启动时覆盖本地配置
- `config/` 和 `download/` 已经通过 `compose.yaml` 挂载到宿主机

## 3. 构建并启动

```bash
docker compose up -d --build
```

启动后访问：

```text
http://服务器IP:8000
```

## 4. 常用命令

查看日志：

```bash
docker compose logs -f
```

重建：

```bash
docker compose up -d --build
```

停止：

```bash
docker compose down
```

查看健康状态：

```bash
docker inspect --format='{{json .State.Health}}' douyin-crawler
curl http://127.0.0.1:8000/api/health
```

## 5. 推荐部署方式

推荐结构：

- 宿主机只开放 `80/443`
- Nginx / Caddy 反向代理到容器 `8000`
- 只把 `config/` 和 `download/` 做持久化
- Cookie 不要写死进镜像，放 `.env`

## 6. 配置建议

只做 API / 搜索 / 轻量采集：

- `2 vCPU`
- `2 GB RAM`
- `20 GB SSD`

单人长期使用，带少量下载：

- `2 vCPU`
- `4 GB RAM`
- `50 GB SSD`

多人共用，带批量下载：

- `4 vCPU`
- `8 GB RAM`
- `100 GB+ SSD`

说明：

- 这个服务更吃网络质量和磁盘空间，不是特别吃 CPU
- 如果主要做搜索和结构化返回，`2C2G` 就能跑
- 如果要大量下载视频/图集，优先加磁盘和带宽，再考虑加 CPU
- 如果后续要公网开放，建议至少上 `2C4G`

## 7. 当前 Docker 镜像特性

- 运行时包含 `node`，用于抖音签名脚本
- 运行时包含 `aria2`，下载功能可直接使用
- 镜像自带健康检查，探测 `/api/health`
