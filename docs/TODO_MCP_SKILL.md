# MCP 与 Skill TODO

这份文档只针对一件事：把当前项目从“人手工操作的爬取工具”往“可被 AI / 外部系统稳定调用的能力服务”推进。

## 先定方向

- [ ] 明确优先级：先做 API 服务稳定化，还是先做 MCP
  说明：如果底层 HTTP API 还在频繁变化，先上 MCP 只会把不稳定接口再包一层。

- [ ] 明确使用场景
  说明：先回答三个问题。
  1. 你是要给自己用，还是给团队 / 客户用？
  2. 你是要让 AI 调用，还是让普通后端系统调用？
  3. 你是要“搜索即返回”，还是“创建任务异步拉结果”？

- [ ] 明确边界
  说明：MCP 适合“让大模型把这个项目当工具来调”；Skill 适合“教代理怎么正确使用你的项目”。两者不是替代关系，通常是 MCP + Skill 配套。

## 推荐落地顺序

- [ ] 第一步：先把现有 HTTP API 定型
  说明：优先稳定这几类能力。
  - `POST /api/settings`
  - `POST /api/search`
  - `POST /api/task/start`
  - `GET /api/task/status`
  - `GET /api/task/results/{task_id}`
  - `GET /api/health`

- [ ] 第二步：补 API 契约和错误码
  说明：MCP 最怕底层接口行为飘。先把成功响应、失败响应、Cookie 失效、风控失败、任务超时这些情况定清楚。

- [ ] 第三步：再做 MCP Server
  说明：MCP Server 不要直接实现爬虫逻辑，应该尽量只做一层适配，把请求转发给现有 HTTP API。

- [ ] 第四步：最后再做 Skill
  说明：Skill 负责教代理什么时候调用哪个 MCP 工具、遇到 Cookie 失效怎么处理、什么时候用同步搜索、什么时候用异步任务。

## MCP 设计 TODO

- [ ] 确定 MCP Server 技术栈
  说明：建议优先 Python，复用现有项目栈；如果你团队更熟 Node，也可以单独起一个 Node MCP 网关。

- [ ] 设计 MCP 工具列表
  说明：建议先做最小集合，不要一开始把所有路由都暴露出去。
  建议首批工具：
  - `douyin_health_check`
  - `douyin_update_settings`
  - `douyin_search_keyword`
  - `douyin_start_task`
  - `douyin_get_task_status`
  - `douyin_get_task_results`

- [ ] 为每个 MCP 工具补清晰 schema
  说明：字段名、是否必填、默认值、错误返回都要固定，不然模型侧容易误用。

- [ ] 统一输入输出
  说明：比如 `keyword`、`limit`、`filters`、`task_id`、`target`、`type` 这些字段命名要保持一致。

- [ ] 补任务轮询策略
  说明：MCP 层要定义清楚异步任务怎么等结果，避免模型无限轮询。

- [ ] 补鉴权方案
  说明：如果 MCP Server 要对外，至少补 API Key 或网关鉴权，不要裸放。

- [ ] 补日志和调用追踪
  说明：要能看出是哪个 MCP 工具触发了哪个 HTTP 请求，失败点在哪一层。

- [ ] 补部署方式
  说明：建议把 MCP Server 和现有 API 服务拆成两个独立进程，避免职责混在一起。

## Skill 设计 TODO

- [ ] 先定义 skill 触发语句
  说明：例如这些请求应该触发这个 skill。
  - “帮我搜索抖音关键词并返回结构化结果”
  - “帮我抓取这个抖音用户主页作品”
  - “Cookie 失效了，先检查配置再重试”
  - “用现有 DouyinCrawler 服务完成搜索 / 采集任务”

- [ ] 确定 skill 名称
  说明：建议叫 `douyin-crawler-ops` 或 `douyin-crawler-mcp`，不要太泛。

- [ ] 给 skill 写清楚使用原则
  说明：至少写明这些规则。
  - 优先调用健康检查
  - 没有 Cookie 时先提示或尝试更新配置
  - 纯关键词场景优先走同步搜索
  - 长耗时采集走异步任务
  - 发现 Cookie 失效时不要无脑重试

- [ ] 给 skill 配 references
  说明：不要把所有细节都堆进 `SKILL.md`，把 API 字段、错误码、部署说明拆到 references。

- [ ] 给 skill 配 examples
  说明：至少准备 3 类示例。
  - 关键词搜索
  - 用户主页采集
  - Cookie 失效处理

- [ ] 给 skill 配 assets / scripts
  说明：如果后面经常需要生成 curl、测试请求或部署片段，可以放到脚本里，不要每次重写。

- [ ] 验证 skill 是否真的有用
  说明：检查它是不是只是在重复 README；如果没有沉淀成“可复用流程”，这个 skill 的价值就不够。

## 目录建议

- [ ] 新建 `mcp/` 或 `mcp_server/`
  说明：放 MCP Server 代码、工具 schema、适配层。

- [ ] 新建 `skills/douyin-crawler-mcp/`
  说明：放 skill 的 `SKILL.md`、`references/`、必要脚本。

- [ ] 新建 `docs/mcp/`
  说明：放 MCP 工具说明、调用示例、部署说明。

## 现阶段最值得先做的 5 件事

- [ ] 给现有 API 补统一错误码和错误结构
- [ ] 给 `POST /api/search` 和任务接口补更完整示例
- [ ] 确定 Cookie 失效检测与告警策略
- [ ] 先做一个最小版 MCP Server，只封装搜索和任务查询
- [ ] 基于 MCP Server 再写一个最小版 Skill

## 不建议现在就做的事

- [ ] 不要一开始就把所有 API 全量映射成 MCP 工具
  说明：工具过多会让模型选择混乱，也会增加维护成本。

- [ ] 不要把 MCP 和业务逻辑写死在同一个模块里
  说明：后面 API 一改，两边会一起炸。

- [ ] 不要先写很长的 Skill 文档
  说明：Skill 应该短、准、能触发，细节放 references。

- [ ] 不要在 Cookie 方案没稳定前做过深封装
  说明：否则你后面会反复改 MCP 和 Skill。

## 结论

- 推荐路线是：先稳定 HTTP API，再做 MCP Server，最后围绕 MCP 补 Skill。
- 你的项目适合做 MCP，因为它已经有清晰的 HTTP API 和任务模型。
- 你的项目也适合做 Skill，但 Skill 不该直接替代 MCP，而应该服务于 MCP 的正确调用。
