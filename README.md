<div align="center">

# 🧭 Interact-EvoAgent

**一个把自主研究/编码 Agent 变成「看得见」的交互系统**

*Web 对话 · 实时 Workflow 轨迹 · 工具与产物可视化 · 全链路可审计、可审批、可复现*

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI%20%2B%20SSE-009688)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/frontend-Next.js%2014-black)](https://nextjs.org/)
[![Backend Tests](https://img.shields.io/badge/backend%20tests-22%20passing-brightgreen)](#-测试)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**EvoAgent 做大脑，也做手** · 开源 Chat UI 做外壳 · Workflow Trace 做亮点

</div>

---

## 📖 项目简介

**Interact-EvoAgent** 在开源 Agent 框架 [**EvoAgent**](README_FRAMEWORK.md) 之上，构建了一个成熟的 **Web 交互系统**。

你在网页里下达任务，系统由 EvoAgent 作为**主 orchestrator（大脑）**驱动，完整执行一条可追踪的生命周期：

```
理解任务 → 记忆检索 → 任务规划 → 工具路由 → 执行 → 反思修正 → 记忆沉淀 → 最终回答
```

每一步都以统一的 **WorkflowEvent** 通过 SSE 实时推送到前端，渲染成可视化的执行轨迹——**只展示可审计的 workflow trace，不暴露模型原始思维链（CoT）**。

EvoAgent 自带完整的原生代码能力（`write_file` / `edit_file` / `apply_patch` / `run_tests` / `git_diff` / `bash` …），因此系统**本身就能自动修改仓库、生成 diff、跑测试修 bug**，无需依赖 Codex / Claude Code；后者仅作为**可选、可插拔**的外部适配器保留。

> 一句话：把「一个能自主研究、自主写代码的 Agent」包装成一个**人能看懂、能干预、能复盘**的产品化界面。

## ✨ 核心特性

| 能力 | 说明 |
| --- | --- |
| 🧠 **真实 EvoAgent 驱动** | `evoagent` 模式跑真实 LLM（DeepSeek），并把 EvoAgent 内部真实工具调用 surface 到 workflow |
| 🧭 **实时 Workflow Trace** | SSE 事件流驱动的富时间线：节点图标、状态徽章、连接线、时长条、running 脉冲动画 |
| 💬 **对话窗口** | Markdown 渲染，改造自开源 Chat UI（`@chatscope/chat-ui-kit-react`） |
| 🔧 **工具 & 产物可视化** | Tool Calls 面板 + Artifacts 面板，内置彩色 **diff 查看器** |
| ⏸️ **审批闭环** | 高风险操作触发 `user.approval.required`，前端 Approve / Reject，后端回 `user.approval.received` |
| 💾 **持久化与回放** | SQLite 落地 `runs / events / artifacts / memories`；历史侧栏点击即可回放任意 run |
| 📊 **统计面板** | 实时 steps / tools / elapsed / status，以及全局聚合统计 |
| 🔐 **安全脱敏** | 事件与产物中的敏感串（API Key 等）自动脱敏后再持久化 |

## 🏗️ 架构

```
┌──────────── Frontend · Next.js（改造开源 Chat UI）────────────┐
│  Chat · Workflow Timeline · Node Detail · Tools · Artifacts   │
│  运行历史 · 统计栏 · 审批控制                                  │
│  只消费 workflow event，不依赖 Agent 内部对象                 │
└───────────────────────────────┬──────────────────────────────┘
                                 │  SSE  /  REST
┌───────────────────────────────▼──────────────────────────────┐
│  Backend · FastAPI + SQLite                                   │
│  InteractiveOrchestrator · WorkflowEvent(v1) · 审批 · 持久化  │
└───────────────────────────────┬──────────────────────────────┘
                                 │
┌───────────────────────────────▼──────────────────────────────┐
│  EvoAgent · 主 orchestrator（大脑 + 手）                      │
│  ReAct loop · 原生代码工具 · memory · 模型路由(DeepSeek)      │
└───────────────────────────────────────────────────────────────┘
```

**设计原则**：开源 UI 做外壳 · EvoAgent 做大脑 · workflow trace 做亮点 · 前端只消费事件、不展示 CoT · 危险操作必须审批。

## 📂 目录结构

```
.
├── evoagent/              # EvoAgent 框架本体（含 Windows 兼容与稳定性修复）
├── backend/               # FastAPI + SSE + SQLite 编排后端
│   ├── app/
│   │   ├── main.py        # REST + SSE 路由
│   │   ├── agent/         # InteractiveOrchestrator + EvoAgent wrapper
│   │   ├── schemas/       # WorkflowEvent v1 等契约
│   │   ├── storage/       # SQLite（runs/events/artifacts/memories）
│   │   └── tools/         # ShellTool + Codex/ClaudeCode 可选适配器
│   ├── tests/             # 22 passing（storage/api/orchestrator）
│   └── CONTRACT.md        # 事件与 API 契约
├── frontend/              # Next.js 前端（改造开源 Chat UI + 富可视化组件）
│   ├── app/               # 页面 + 设计系统
│   ├── components/        # Chat / Workflow / NodeDetail / Tools / Artifacts / Diff / History / Stats
│   └── lib/               # api-client / event-client / ui 工具
├── README.md              # 本文件（项目首页）
├── README_INTERACTIVE.md  # 交互系统完整文档（API、功能、启动）
└── README_FRAMEWORK.md    # EvoAgent 框架原始文档
```

## 🚀 快速开始

### 后端

```bash
cd backend
python -m pip install -r requirements.txt

# 真实模式需要 DeepSeek Key；不设置则自动降级为 mock，可无 Key 演示完整工作流
export DEEPSEEK_API_KEY="sk-..."

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端

```bash
cd frontend
npm install
export NEXT_PUBLIC_BACKEND_URL="http://localhost:8000"
npm run dev          # 打开 http://localhost:3000
```

在页面右上角切换模式：`mock`（无 Key 演示）或 `evoagent`（真实 EvoAgent）。

## 🔌 API 一览

| Method & Path | 用途 |
| --- | --- |
| `POST /runs` | 创建一次运行（`mode`: `mock` \| `evoagent`） |
| `GET /runs` | 运行列表（含 tool_count / event_count / duration_ms 指标） |
| `GET /runs/{id}` | 运行状态 + 产物 |
| `GET /runs/{id}/events` | **SSE** 事件流 |
| `GET /runs/{id}/events/list` | 事件 JSON 回放（按 seq 有序） |
| `POST /runs/{id}/approve` | 审批（approve / reject） |
| `POST /runs/{id}/resume` | 恢复暂停的运行 |
| `GET /runs/{id}/artifacts` · `GET /artifacts/{id}` | 产物列表 / 详情（diff、测试输出） |
| `GET /runs/{id}/memories` · `GET /memories` | 记忆记录 |
| `GET /stats` | 全局聚合统计 |
| `POST /runs/{id}/feedback` | 提交评分 / 反馈 |

完整说明见 **[README_INTERACTIVE.md](README_INTERACTIVE.md)**。

## 🧪 测试

```bash
# 交互系统后端
cd backend && python -m pytest -q        # 22 passing

# 前端类型检查 + 生产构建
cd frontend && npm run build

# EvoAgent 框架（可选）
pytest -q                                # 694 passing, 5 skipped
```

真实 API 端到端已验证：mock / evoagent 全流程、ShellTool 与 EvoAgent 原生代码工具（write_file / git_diff / run_tests）surface、审批闭环（暂停 → 拒绝→tool.failed / 批准→approval.received）。

## 🙏 致谢

- 底层 Agent 框架：[EvoAgent](README_FRAMEWORK.md)（MIT）
- 前端聊天基座：[@chatscope/chat-ui-kit-react](https://github.com/chatscope/chat-ui-kit-react)（MIT）

## 📄 许可

基于 EvoAgent，遵循 [MIT License](LICENSE)。
