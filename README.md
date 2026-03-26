# ✨DouyinCrawler

**[English](./README_EN.md) | [Tiếng Việt](./README_VI.md) | 简体中文**

## 📢声明

> 本项目初衷为学习`python`爬虫、命令行调用`Aria2`及`python`实现`WebUI`的案例，后用于尝试体验AI编程（前端及前后端交互部分纯AI生成），应用程序功能为获取抖音平台上公开的信息，仅用于测试和学习研究，禁止用于商业用途或任何非法用途。
>
> 任何用户直接或间接使用、传播本仓库内容时责任自负，本仓库的贡献者不对该等行为产生的任何后果负责。
>
> **如果相关方认为该项目的代码可能涉嫌侵犯其权利，请及时联系我删除相关代码**。
>
> 使用本仓库的内容即表示您同意本免责声明的所有条款和条件。如果你不接受以上的免责声明，请立即停止使用本项目。

---

## 🍬功能特性

### 📊 数据采集
- ✅ 单个作品数据
- ✅ 用户主页作品
- ✅ 用户喜欢作品（需目标开放权限）
- ✅ 用户收藏作品（需目标开放权限）
- ✅ 话题挑战作品
- ✅ 合集作品
- ✅ 音乐原声作品
- ✅ 关键词搜索作品
- ✅ 关注用户（仅cli模式，需目标开放权限）
- ✅ 粉丝用户（仅cli模式，需目标开放权限）

### 🎯 应用特性
- 🔄 **增量采集**：智能增量采集用户主页作品
- ⬇️ **批量下载**：集成 Aria2，支持视频/图片批量下载
- 🎨 **多种模式**：GUI 桌面应用 / Web 服务 / cli命令行
- 🌐 **RESTful API**：v2.0 提供完整的 HTTP API
- 🔧 **跨平台支持**：Windows / macOS / Linux

### 🧭 项目定位
- 这个项目不是只做“抖音搜索”，搜索只是其中一种采集入口。
- 当前采集能力覆盖：单作品、用户主页、喜欢、收藏、话题、合集、音乐、关键词搜索、关注列表、粉丝列表。
- 对外调用既支持异步任务模式（`/api/task/*` + `/api/events`），也支持同步关键词搜索接口（`POST /api/search`）。

## 📸 界面展示

![软件界面](./docs/images/main.png)

## 🚀快速开始

### 环境要求

> 📍测试环境：`Win10 x64` + `Python 3.12` + `Node.js 22.13.0` + `uv 0.9+`

### Windows 用户

下载发布包后，解压并运行 `DouyinCrawler.exe`

### Web 服务（Docker / 全平台）

```bash
# Docker（推荐）
docker compose up -d

# 或手动启动
uv sync 
cd frontend && pnpm install && pnpm build && cd ..
python -m backend.server
```

浏览器访问 `http://localhost:8000`

如果你准备长期部署或对外暴露接口，建议同时准备 `.env`：

```env
DOUYIN_COOKIE=你的抖音 Cookie
DOUYIN_USER_AGENT=与 Cookie 对应的 User-Agent
```

仓库已提供示例文件：[.env.example](./.env.example)

> 💡 Cookie 维护说明
> - GUI / Web 服务都可以通过 `POST /api/settings` 在线更新 `cookie` 和 `userAgent`，新任务会直接读取最新配置，不需要重启。
> - GUI 模式还支持“登录获取 Cookie”。
> - 只有你手动编辑 `config/settings.json` 文件时，运行中的进程不会自动热加载，这种场景才需要重启。
> - Docker Compose 已默认挂载 `./config` 和 `./download`，配置和下载文件不会因为容器重建而丢失。

### 命令行（cli模式）

```bash
python -m backend.cli -u https://www.douyin.com/user/xxx -l 20
```

📖 详细使用说明请查看 [USAGE.md](USAGE.md)

📡 HTTP API 说明请查看 [docs/API.md](./docs/API.md)

🐳 Docker 部署说明请查看 [docs/DEPLOY.md](./docs/DEPLOY.md)

📝 后续优化与部署代办请查看 [docs/TODO.md](./docs/TODO.md)

## 🔨构建和打包

```powershell
# 交互式菜单
.\quick-start.ps1

# 或直接打包
.\scripts\build\pyinstaller.ps1
```

脚本目录结构：
```
scripts/
├── build/          # 打包脚本 (PyInstaller / Nuitka)
├── setup/          # 环境配置 (uv / aria2)
└── dev.ps1         # 开发环境构建
```

## 📊 技术栈

- **后端**: Python 3.12, FastAPI, PyWebView
- **前端**: React 18, TypeScript, Vite
- **下载**: Aria2
- **打包**: PyInstaller / Nuitka

