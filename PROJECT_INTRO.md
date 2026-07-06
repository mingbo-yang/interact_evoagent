# Interact-EvoAgent · 交互式自主研究工作流系统

> 一个把 **EvoAgent**（自主研究/编码 Agent 框架）包装成 **可视化交互系统** 的项目：
> 左侧对话、右侧实时 workflow 轨迹、底部工具调用与产物展示，全链路可审计、可审批、可复现。

<div align="center">

**EvoAgent 做大脑，也做手** · Web UI 做外壳 · Workflow Trace 做亮点

</div>

---

## 这是什么

本项目在开源 Agent 框架 **EvoAgent** 之上，构建了一个成熟的 Web 交互系统。用户在网页里下达任务，系统由 EvoAgent 作为**主 orchestrator** 驱动，完整执行「理解 → 记忆检索 → 规划 → 工具路由 → 执行 → 反思 → 记忆沉淀 → 回答」的生命周期，并把每一步以 **workflow event** 实时推送到前端可视化，而**不暴露模型原始思维链（CoT）**。

EvoAgent 自带完整的代码能力（`write_file` / `edit_file` / `apply_patch` / `run_tests` / `git_diff` / `bash` 等），因此系统**本身就能自动改仓库、生成 diff、跑测试修 bug**，无需依赖 Codex / Claude Code；后者仅作为可选、可插拔的外部适配器保留。

## 核心特性

- **实时 Workflow Trace**：SSE 事件流驱动的富时间线（节点图标、状态徽章、连接线、时长条、running 脉冲动画）。
- **对话窗口**：Markdown 渲染，改造自开源 Chat UI（`@chatscope/chat-ui-kit-react`）。
- **工具与产物可视化**：Tool Calls 面板 + Artifacts 面板（内置彩色 **diff 查看器**）。
- **真实 EvoAgent 接入**：`evoagent` 模式跑真实 LLM（DeepSeek），并把 EvoAgent 内部真实工具调用 surface 到 workflow。
- **审批闭环**：高风险操作触发 `user.approval.required`，前端可 Approve / Reject，后端回 `user.approval.received`。
- **持久化与回放**：SQLite 落地 `runs / events / artifacts / memories`；运行历史侧栏可点击回放。
- **统计面板**：实时 steps / tools / elapsed / status，以及全局聚合统计。
- **安全**：事件与产物敏感串（API Key 等）自动脱敏后再持久化。

## 架构

```
┌──────────── Frontend (Next.js, 改造开源 Chat UI) ────────────┐
│  Chat · Workflow Timeline · Node Detail · Tools · Artifacts  │
│  只消费 workflow event，不依赖 Agent 内部对象                 │
└───────────────────────────────┬──────────────────────────────┘
                                 │  SSE / REST
┌───────────────────────────────▼──────────────────────────────┐
│  Backend (FastAPI + SQLite)                                   │
│  InteractiveOrchestrator · WorkflowEvent(v1) · 审批 · 持久化  │
└───────────────────────────────┬──────────────────────────────┘
                                 │
┌───────────────────────────────▼──────────────────────────────┐
│  EvoAgent (主 orchestrator / 大脑 + 手)                       │
│  ReAct loop · 原生代码工具 · memory · 模型路由(DeepSeek)      │
└───────────────────────────────────────────────────────────────┘
```

目录：

- `evoagent/` — EvoAgent 框架本体（含 Windows 兼容与稳定性修复）。
- `backend/` — FastAPI + SSE + SQLite 编排后端（`app/`）与测试（`tests/`，22 passing）。
- `frontend/` — Next.js 前端（改造开源 Chat UI + 富可视化组件）。
- `README_INTERACTIVE.md` — 交互系统完整文档（API 参考、前端功能、启动方式）。

## 快速开始

**后端**

```bash
cd backend
python -m pip install -r requirements.txt
# 真实模式需要 DeepSeek Key；不设置则自动降级为 mock
export DEEPSEEK_API_KEY="sk-..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**前端**

```bash
cd frontend
npm install
export NEXT_PUBLIC_BACKEND_URL="http://localhost:8000"
npm run dev   # 打开 http://localhost:3000
```

选择 `mock` 模式可无 Key 演示完整工作流；选择 `evoagent` 模式跑真实 EvoAgent。

## API 一览

`POST /runs` · `GET /runs` · `GET /runs/{id}` · `GET /runs/{id}/events`(SSE) ·
`GET /runs/{id}/events/list` · `POST /runs/{id}/approve` · `POST /runs/{id}/resume` ·
`GET /runs/{id}/artifacts` · `GET /artifacts/{id}` · `GET /runs/{id}/memories` ·
`GET /memories` · `GET /stats` · `POST /runs/{id}/feedback`

完整说明见 [README_INTERACTIVE.md](README_INTERACTIVE.md)。

## 测试

```bash
# 交互系统后端
cd backend && python -m pytest -q          # 22 passing

# EvoAgent 框架
cd .. && pytest -q                          # 694 passing, 5 skipped

# 前端类型检查 + 构建
cd frontend && npm run build
```

## 许可

基于 EvoAgent（MIT）。详见 [LICENSE](LICENSE)。
