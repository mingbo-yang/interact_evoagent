# EvoAgent 架构设计文档

**版本**: 0.1.0-draft  
**最后更新**: 2025-07-18  
**状态**: Phase 0 — 架构设计

---

## 1. 项目定位

### 1.1 EvoAgent 是什么

EvoAgent 是一个 **模型无关、工具无关、状态驱动、可观测、可恢复** 的开源 Agent 框架。它提供从单轮对话到多 Agent 协作的完整基础设施，目标是在功能完整性、工程可扩展性和研究友好性上对标主流框架。

### 1.2 面向场景

| 场景 | 说明 |
|------|------|
| Code Agent | 真实代码仓库的分析、修改、测试、修复 |
| Research Agent | 多步推理、文献检索、假设验证 |
| Workflow Agent | DAG / 条件分支 / human-in-the-loop |
| Multi-Agent | Supervisor、Debate、Pipeline 协作 |
| RAG Agent | 文档问答、知识库检索增强 |
| CLI Assistant | 终端交互式编程助手 |

### 1.3 能力对标

| 框架 | EvoAgent 对标策略 |
|------|-------------------|
| LangGraph | Workflow Graph（节点/边/条件边/checkpoint），但不绑 LangChain |
| AutoGen | Multi-Agent 协作（RoleAgent / Supervisor / Debate），但不绑 OpenAI |
| OpenHands | Code Agent + Sandbox + Permissions，但更模块化 |
| SWE-agent | Code Agent 专项能力，但支持更多 LLM 后端 |
| Dify | 可视化编排的底层引擎能力，通过 API 暴露 |
| smolagents | HuggingFace 生态的轻量能力，通过 ModelProvider 兼容 |

### 1.4 双重目标

- **工程落地**: 每个模块可独立使用、独立测试、独立发布
- **研究友好**: 所有中间状态可导出（JSONL Trace），支持 ablation study 和 benchmark

---

## 2. 核心设计原则

| 原则 | 含义 |
|------|------|
| **model-agnostic** | 不绑死任何 LLM 厂商，通过 `ModelProvider` / `ModelRouter` 抽象 |
| **tool-agnostic** | 工具通过 `ToolRegistry` 注册，统一 `ToolResult`，不区分内置/外置 |
| **state-driven** | 所有运行时状态存 `RuntimeState`，支持 checkpoint / resume |
| **observable** | 所有 LLM 调用、Tool 调用、文件修改、错误、结果都写入 `EventLogger` |
| **resumable** | 长任务中断后可恢复，不丢失中间状态 |
| **safe-by-default** | 敏感操作（shell / 文件写 / 代码执行）默认经 `PermissionPolicy` |
| **test-first** | 每个模块必须有单元测试，mock 掉外部依赖（LLM / shell） |
| **extensible-by-interface** | 通过抽象基类扩展，不通过 monkey-patch |

---

## 3. 总体架构图

```
                            ┌──────────────────────┐
                            │      User Task        │
                            └──────────┬───────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Agent Runtime                                │
│                                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────┐  │
│  │ Context  │──▶│ Planner  │──▶│ Executor │──▶│ Critic/Reflector │  │
│  │ Builder  │   │          │   │          │   │                  │  │
│  └──────────┘   └──────────┘   └─────┬────┘   └────────┬─────────┘  │
│                                      │                 │            │
│                    ┌─────────────────┼─────────────────┘            │
│                    ▼                 ▼                              │
│  ┌──────────────────────┐  ┌──────────────────────┐                 │
│  │   Tools / Sandbox    │  │   ModelProvider      │                 │
│  │   ┌──────────────┐   │  │   (DeepSeek/OpenAI/  │                 │
│  │   │ ToolRegistry │   │  │    LiteLLM/Local)    │                 │
│  │   │ Permission   │   │  └──────────────────────┘                 │
│  │   │ Sandbox      │   │                                           │
│  │   └──────────────┘   │                                           │
│  └──────────────────────┘                                           │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   Memory System                               │   │
│  │  Working │ Episodic │ Semantic │ Procedural │ Reflection     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Event Logger / Trace Recorder                    │   │
│  │         (JSONL events + run_id + step_id + checkpoint)        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│                            │                                         │
│                            ▼                                         │
│                   ┌────────────────┐                                 │
│                   │  Final Result  │                                 │
│                   └────────────────┘                                 │
└──────────────────────────────────────────────────────────────────────┘
```

**数据流简述**:

1. User Task 进入 Agent Runtime
2. Context Builder 组装 system prompt + memory + tools schema
3. Planner 生成 Plan（可多步）
4. Executor 逐步执行：LLM 推理 → Tool 调用 → Sandbox 执行 → 结果回传
5. Critic/Reflector 评估执行结果，决定是否重试/修正
6. Memory Writer 将关键信息写入 memory
7. Event Logger 全程记录 JSONL trace
8. 最终返回 AgentResult

---

## 4. 目录结构设计

```
evoagent/
├── core/               # 核心抽象和运行时
│   ├── __init__.py
│   ├── types.py        # Message, ToolCall, ToolResult, RuntimeState 等
│   ├── runtime.py      # AgentRuntime 主循环
│   ├── context.py      # ContextBuilder
│   └── errors.py       # 统一异常体系
│
├── models/             # ModelProvider / ModelRouter
│   ├── __init__.py
│   ├── base.py         # BaseModelProvider 抽象
│   ├── router.py       # ModelRouter
│   ├── deepseek.py     # DeepSeek 适配
│   ├── openai_compat.py # OpenAI-compatible 通用适配
│   └── litellm.py      # LiteLLM 适配（多模型统一）
│
├── tools/              # Tool System
│   ├── __init__.py
│   ├── base.py         # BaseTool, ToolRegistry, ToolResult
│   ├── file.py         # 文件读写工具
│   ├── search.py       # 代码搜索（grep / AST）
│   ├── shell.py        # shell 命令执行
│   ├── python.py       # Python 代码执行
│   ├── git.py          # Git 操作
│   └── mcp.py          # MCP 协议支持（后续）
│
├── sandbox/            # Sandbox / Permissions
│   ├── __init__.py
│   ├── policy.py       # PermissionPolicy (review/auto/yolo)
│   ├── sandbox.py      # Sandbox 抽象
│   └── local.py        # 本地 sandbox 实现
│
├── memory/             # Memory System
│   ├── __init__.py
│   ├── base.py         # BaseMemory, MemoryItem
│   ├── working.py      # WorkingMemory
│   ├── episodic.py     # EpisodicMemory
│   ├── semantic.py     # SemanticMemory
│   ├── procedural.py   # ProceduralMemory
│   └── reflection.py   # ReflectionMemory
│
├── planning/           # Planner / Executor / Critic
│   ├── __init__.py
│   ├── planner.py      # Planner 抽象 + 实现
│   ├── executor.py     # Executor
│   └── critic.py       # Critic / Reflector
│
├── workflow/           # Workflow Graph
│   ├── __init__.py
│   ├── graph.py        # WorkflowGraph
│   ├── node.py         # WorkflowNode
│   └── edge.py         # Edge / ConditionEdge
│
├── multi_agent/        # Multi-Agent
│   ├── __init__.py
│   ├── role.py         # RoleAgent
│   ├── supervisor.py   # Supervisor
│   ├── debate.py       # Debate
│   └── pipeline.py     # Pipeline
│
├── rag/                # RAG / Knowledge Base
│   ├── __init__.py
│   ├── loader.py       # 文档加载
│   ├── splitter.py     # 文档切分
│   ├── retriever.py    # 检索
│   └── citation.py     # 引用追踪
│
├── skills/             # Skill System
│   ├── __init__.py
│   ├── registry.py     # SkillRegistry
│   ├── loader.py       # SkillLoader
│   └── evaluator.py    # SkillEvaluator
│
├── logging/            # Event Logger / Trace
│   ├── __init__.py
│   ├── logger.py       # EventLogger (JSONL)
│   ├── trace.py        # TraceRecorder
│   └── checkpoint.py   # Checkpoint 管理
│
├── eval/               # Evaluation Harness
│   ├── __init__.py
│   ├── harness.py      # EvalHarness
│   ├── tasks.py        # EvalTask 定义
│   └── metrics.py      # EvalResult 指标
│
├── config/             # 配置管理
│   ├── __init__.py
│   └── loader.py       # 从 YAML + 环境变量加载
│
├── cli/                # CLI
│   ├── __init__.py
│   ├── main.py         # 入口 (init/chat/code/run/eval/memory/trace/config)
│   └── commands/       # 各子命令
│
└── __init__.py          # 版本号 + 顶层导出

tests/                   # 单元测试（镜像 src 结构）
examples/                # 可运行样例
docs/                    # 文档
```

---

## 5. 模块边界

### 5.1 core
- **负责**: 核心类型定义、Runtime 主循环、Context 组装、异常体系
- **不负责**: 不直接调用 LLM（委托 models）、不直接执行工具（委托 tools）
- **输入**: User task string / message list
- **输出**: AgentResult
- **交互**: 调用 models / tools / sandbox / memory / planning / logging
- **扩展**: 通过 Runtime 的 hook 机制注入自定义行为

### 5.2 models
- **负责**: LLM 调用的统一抽象，路由，重试，token 计数
- **不负责**: 不解析工具调用结果（由 tools 负责）
- **输入**: LLMRequest (messages + tools schema + config)
- **输出**: LLMResponse (content + tool_calls + usage)
- **交互**: 只被 core/planning 调用，不主动调用其他模块
- **扩展**: 实现 `BaseModelProvider` 即可接入新模型

### 5.3 tools
- **负责**: 工具注册、schema 暴露、参数校验、执行、结果标准化
- **不负责**: 不决定何时调用工具（由 planning 决定），不做权限检查（委托 sandbox）
- **输入**: ToolCall (name + arguments)
- **输出**: ToolResult (success/fail + output + error)
- **交互**: 被 planning/executor 调用，调用 sandbox 做权限检查
- **扩展**: 继承 `BaseTool` 注册到 `ToolRegistry`

### 5.4 sandbox
- **负责**: 权限策略（review/auto/yolo）、沙箱执行环境、回滚
- **不负责**: 不定义工具有哪些（由 tools 负责）
- **输入**: 操作类型 + 参数 + 权限模式
- **输出**: 允许/拒绝/需确认 + 执行结果
- **交互**: 被 tools 调用，记录事件到 logging
- **扩展**: 实现 `BaseSandbox` 支持 Docker / E2B 等远端沙箱

### 5.5 memory
- **负责**: 存储、检索、写入、整合、评估各类 memory
- **不负责**: 不决定 Agent 行为（由 planning 使用 memory 结果）
- **输入**: 检索查询 / 写入内容
- **输出**: 检索结果 / 写入确认
- **交互**: 被 core/planning 读取，被 critic 写入
- **扩展**: 实现 `BaseMemory` 接入向量数据库 / 图数据库

### 5.6 planning
- **负责**: 任务分解（Planner）、步骤执行（Executor）、结果评估（Critic）
- **不负责**: 不直接操作文件或网络（委托 tools）
- **输入**: Task + Context + Memory
- **输出**: Plan → 执行结果 → 评估反馈
- **交互**: 调用 models / tools / sandbox / memory / logging
- **扩展**: 实现 `BasePlanner` / `BaseCritic` 接入不同策略

### 5.7 workflow
- **负责**: DAG 图定义、节点执行、条件路由、checkpoint、human interrupt
- **不负责**: 不定义单步如何执行（由 planning 负责）
- **输入**: WorkflowGraph 定义
- **输出**: 图执行结果 + checkpoint
- **交互**: 调用 planning/executor 执行每个节点
- **扩展**: 自定义 Node / Edge 类型

### 5.8 multi_agent
- **负责**: 多 Agent 协作模式（Role / Supervisor / Debate / Pipeline）
- **不负责**: 不实现单个 Agent 的核心循环（由 core 负责）
- **输入**: 多个 RoleAgent + 协作策略
- **输出**: 协作结果
- **交互**: 每个子 Agent 复用 core.runtime
- **扩展**: 实现新的协作模式

### 5.9 rag
- **负责**: 文档加载、切分、检索、引用追踪
- **不负责**: 不执行 LLM 推理（由 models 负责）
- **输入**: 文档路径 / URL / 查询
- **输出**: 检索结果 + 引用
- **交互**: 被 core/context 调用，向 memory 写入
- **扩展**: 实现自定义 Loader / Splitter / Retriever

### 5.10 skills
- **负责**: 可复用技能的加载、注册、检索、使用、评估
- **不负责**: 不执行底层工具调用（委托 tools）
- **输入**: Skill 名称 + 参数
- **输出**: Skill 执行结果
- **交互**: 调用 tools，被 planning 调用
- **扩展**: 从文件/远程加载 Skill 定义

### 5.11 logging
- **负责**: JSONL 事件记录、trace 追踪、checkpoint 管理
- **不负责**: 不修改 Agent 行为
- **输入**: Event 对象
- **输出**: 写入的日志文件路径 + checkpoint 数据
- **交互**: 被所有其他模块调用
- **扩展**: 实现自定义 EventSink（数据库、消息队列）

### 5.12 eval
- **负责**: benchmark 定义、执行、指标计算
- **不负责**: 不修改 Agent 行为
- **输入**: EvalTask 列表
- **输出**: EvalResult 汇总
- **交互**: 调用 Agent Runtime 执行任务
- **扩展**: 实现自定义 EvalTask

### 5.13 config
- **负责**: YAML + 环境变量配置加载、校验
- **不负责**: 不包含业务逻辑
- **输入**: 配置文件路径
- **输出**: 类型化的配置对象
- **交互**: 被所有模块在初始化时调用

### 5.14 cli
- **负责**: 命令行入口、参数解析、子命令分发
- **不负责**: 不包含 Agent 核心逻辑
- **输入**: 命令行参数
- **输出**: 终端输出
- **交互**: 调用所有其他模块

---

## 6. 核心抽象

### 6.1 Message

```python
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None          # 可选发送者名称
    tool_call_id: str | None  # tool 角色时必填
    tool_calls: list[ToolCall] | None  # assistant 角色时可能有
    metadata: dict             # 额外信息（token 数等）
```

### 6.2 ToolCall

```python
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
```

### 6.3 ToolResult

```python
class ToolResult:
    call_id: str
    tool_name: str
    success: bool
    output: str
    error: str | None
    artifacts: list[str]   # 产生的文件路径列表
    duration_ms: int
```

### 6.4 LLMRequest

```python
class LLMRequest:
    messages: list[Message]
    tools: list[dict] | None        # function-calling schema
    model: str
    temperature: float
    max_tokens: int
    stop: list[str] | None
    metadata: dict
```

### 6.5 LLMResponse

```python
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] | None
    finish_reason: str       # "stop" | "tool_calls" | "length" | "error"
    usage: Usage
    model: str
    latency_ms: int
```

### 6.6 Plan

```python
class Plan:
    id: str
    task: str
    steps: list[PlanStep]
    created_at: datetime
    status: Literal["pending", "running", "completed", "failed"]

class PlanStep:
    id: str
    description: str
    expected_tool: str | None
    status: Literal["pending", "running", "completed", "failed", "skipped"]
    result: ToolResult | None
```

### 6.7 RuntimeState

```python
class RuntimeState:
    run_id: str
    step_id: str
    phase: str                      # 当前阶段: planning/executing/critic/recovery
    messages: list[Message]
    plan: Plan | None
    memory_snapshot: dict
    tool_results: list[ToolResult]
    errors: list[str]
    checkpoints: list[Checkpoint]
    created_at: datetime
    updated_at: datetime
    metadata: dict

class Checkpoint:
    id: str
    state: RuntimeState
    timestamp: datetime
    can_resume: bool
```

### 6.8 AgentResult

```python
class AgentResult:
    run_id: str
    success: bool
    final_output: str
    steps_taken: int
    tool_calls: list[ToolResult]
    total_tokens: int
    total_cost: float
    duration_ms: int
    errors: list[str]
    artifacts: list[str]
```

### 6.9 Event

```python
class Event:
    event_id: str
    run_id: str
    step_id: str
    timestamp: datetime
    event_type: str              # llm_call | tool_call | file_write | shell_exec |
                                 # memory_write | error | checkpoint | result
    data: dict
    metadata: dict
```

### 6.10 MemoryItem

```python
class MemoryItem:
    id: str
    memory_type: Literal["working", "episodic", "semantic", "procedural", "reflection"]
    content: str
    embedding: list[float] | None
    importance: float            # 0.0 ~ 1.0
    access_count: int
    created_at: datetime
    last_accessed_at: datetime
    metadata: dict
```

### 6.11 WorkflowNode

```python
class WorkflowNode:
    id: str
    name: str
    fn: Callable[[RuntimeState], RuntimeState]
    retry: int                   # 失败重试次数
    timeout_sec: int

class WorkflowEdge:
    source: str
    target: str
    condition: Callable[[RuntimeState], bool] | None  # None = 无条件
```

### 6.12 RoleAgent

```python
class RoleAgent:
    name: str
    role_description: str         # system prompt 的角色描述
    tools: list[str]              # 可用工具名列表
    model: str                    # 使用的模型
    runtime: AgentRuntime         # 复用核心运行时
```

### 6.13 EvalTask / EvalResult

```python
class EvalTask:
    id: str
    description: str
    input: str
    expected_output: str | None
    expected_tools: list[str] | None
    max_steps: int
    success_criteria: Callable[[AgentResult], bool]

class EvalResult:
    task_id: str
    agent_result: AgentResult
    passed: bool
    metrics: dict                 # steps, tokens, cost, duration, ...
```

---

## 7. Agent 执行流程

### 7.1 普通 Chat Agent

```
User Input
  → ContextBuilder: system_prompt + user_msg
  → LLM call (no tools)
  → Response → AgentResult
```

### 7.2 Tool-Use Agent

```
User Input
  → ContextBuilder: system_prompt + tools_schema + user_msg
  → Loop:
      → LLM call
      → if tool_calls:
          → PermissionPolicy.check(tool_name, args)
          → Sandbox.execute(tool_name, args)
          → append ToolResult to messages
      → if no tool_calls:
          → break
  → Critic.assess(result)
  → if fail: retry (max N times)
  → AgentResult
```

### 7.3 Code Agent

```
User Input (coding task)
  → ContextBuilder: code_agent_system_prompt + repo context + user_msg
  → Planner: generate Plan (read → analyze → edit → test → fix)
  → Executor loop per step:
      → LLM call with tools (read_file, write_file, shell, git)
      → Sandbox.execute with code-specific permissions
  → Critic: verify tests pass, code style ok
  → AgentResult (with diff artifacts)
```

### 7.4 Memory Agent

```
User Input
  → Memory.retrieve(query) → relevant memories
  → ContextBuilder: system_prompt + memories + user_msg
  → Agent loop (as tool-use agent)
  → Memory.write(new observations)
  → Memory.consolidate()  # 定期整合
  → AgentResult
```

### 7.5 Multi-Agent Pipeline

```
User Input
  → Supervisor.decompose(task) → sub-tasks
  → for each sub-task:
      → RoleAgent.run(sub-task)
      → aggregate results
  → Final synthesis
  → AgentResult
```

### 7.6 Workflow Graph Agent

```
User Input
  → WorkflowGraph.load(graph_def)
  → for each node in topological order:
      → if condition_edge: evaluate condition
      → node.fn(state) → new_state
      → CheckpointManager.save(state)
  → AgentResult
```

---

## 8. Tool Calling 流程

```
1. 工具注册
   tool = MyTool()
   ToolRegistry.register(tool)
   → 生成 OpenAI function-calling schema

2. Schema 暴露
   ContextBuilder.build_tools_section()
   → 将 ToolRegistry 中的所有 schema 注入 system prompt / API tools 参数

3. LLM 生成 tool_call
   response = ModelProvider.chat(messages, tools=schemas)
   → 解析 response.tool_calls

4. 参数校验
   for each tool_call:
       tool = ToolRegistry.get(tool_call.name)
       tool.validate(tool_call.arguments)
       → ValidationError 或 通过

5. 权限检查
   PermissionPolicy.check(
       tool_name=tool_call.name,
       arguments=tool_call.arguments,
       mode=config.permission_mode  # review | auto | yolo
   )
   → allow / deny / ask_user

6. Sandbox 执行
   result = Sandbox.execute(tool_call)
   → 隔离执行，超时 kill，资源限制

7. 结果标准化
   ToolResult(success=..., output=..., error=..., artifacts=..., duration_ms=...)

8. Event Logging
   EventLogger.log(Event(event_type="tool_call", data={...}))

9. Error Recovery
   if not result.success:
       Critic.diagnose(result.error)
       → 决定 retry / skip / abort
```

---

## 9. Memory 流程

### 9.1 Memory Retrieval

```
Query → Embedding (if configured) → Vector Search + Keyword Search
  → Merge & Rank → Top-K MemoryItems
  → Filter by importance / recency / relevance
  → Return formatted context string
```

### 9.2 Memory Injection

```
ContextBuilder.build():
    memories = Memory.retrieve(user_msg)
    system_prompt += format_memories(memories)
```

### 9.3 Memory Writing

```
Critic evaluates each step:
    if observation is important:
        Memory.write(MemoryItem(
            type="episodic",
            content=summary,
            importance=score,
        ))
```

### 9.4 Memory Consolidation

```
Periodic / on threshold:
    similar episodic memories → merge into semantic memory
    successful tool patterns → store as procedural memory
    failed attempts → store as reflection memory
```

### 9.5 Memory Evolution

```
Long-term: old low-importance memories decay
Reinforcement: high-access memories boost importance
```

### 9.6 Memory Evaluation

```
Metrics:
    memory_hit_rate: 检索命中率
    memory_contribution: memory 对任务成功率的贡献
    memory_size: 存储占用
    retrieval_latency: 检索延迟
```

---

## 10. Sandbox 和权限系统

### 10.1 三种模式

| 模式 | 行为 |
|------|------|
| **review** | 每个敏感操作弹出确认，用户 approve/deny。默认模式。 |
| **auto** | 允许读写工作目录内的文件，允许执行白名单命令。危险操作仍需确认。 |
| **yolo** | 所有操作自动允许。仅用于可信环境和自动化测试。 |

### 10.2 优先级

```
deny > ask > allow > fallback

1. deny 列表:   rm -rf /, curl | sh, 敏感路径
2. ask 列表:    工作目录外的写入, 网络请求, git push
3. allow 列表:  工作目录内读写, 白名单命令, 纯计算
4. fallback:    未分类操作 → 按模式处理
                review → ask
                auto → ask (if outside workspace) / allow
                yolo → allow
```

### 10.3 审计

所有权限决策记录到 EventLogger，包括用户的选择（approve/deny）。

---

## 11. Observability

### 11.1 JSONL Event Log

```
每行一个 Event JSON:
{"event_id":"evt-001","run_id":"run-abc","step_id":"step-1","timestamp":"...","event_type":"llm_call","data":{...}}
```

### 11.2 Trace

```
一个 run_id 下所有 event 按 step_id 组合成完整 trace。
支持回放：按 event 序列重新执行。
```

### 11.3 关键 ID

```
run_id:    一次用户任务
step_id:   任务内的一次 Agent 循环
turn_id:   一次 LLM 调用 + 其 tool_calls
```

### 11.4 Checkpoint

```
每个 step 结束自动保存 RuntimeState。
支持从任意 checkpoint resume。
```

### 11.5 Diff Record

```
Code Agent 的文件修改自动记录 unified diff。
```

### 11.6 Final Result

```
AgentResult 包含所有关键指标的汇总。
```

---

## 12. Evaluation

### 12.1 指标

| 指标 | 说明 |
|------|------|
| task_success_rate | 任务成功率 |
| pass_rate | benchmark 通过率 |
| avg_steps | 平均执行步数 |
| avg_tool_calls | 平均工具调用次数 |
| avg_llm_calls | 平均 LLM 调用次数 |
| avg_runtime | 平均执行时间 |
| cost | 总 token 成本 |
| memory_hit_rate | memory 检索命中率 |
| recovery_success_rate | 从错误中恢复的成功率 |

### 12.2 Benchmark 层次

```
Level 1 — Toy: 数学运算、简单问答
Level 2 — Tool: 文件操作、代码搜索
Level 3 — Code: SWE-bench 风格代码修复
Level 4 — Agent: 多步推理、多工具协调
Level 5 — Multi-Agent: 协作任务
```

---

## 13. 开发阶段

| Phase | 目标 | 验收标准 |
|-------|------|----------|
| **0** | 架构设计文档 | 本文档完成 + 评审通过 |
| **1** | Core Schema + 项目骨架 | 所有核心类型定义，pyproject.toml，compileall 通过 |
| **2** | ModelProvider | DeepSeek + OpenAI-compatible 适配，mock 测试通过 |
| **3** | Tool System | ToolRegistry + 5 个基础工具 + ToolResult + 单元测试 |
| **4** | PermissionPolicy / Sandbox | review/auto/yolo 三种模式 + 单元测试 |
| **5** | EventLogger / TraceRecorder | JSONL 日志 + trace 回放 + 单元测试 |
| **6** | Planner / Executor / Critic | ReAct 循环 + Plan 生成 + 错误恢复 + 集成测试 |
| **7** | RuntimeState / Checkpoint | 状态记录 + checkpoint + resume + 测试 |
| **8** | CLI (basic) | init / chat / run / code 子命令可用 |
| **9** | Memory System | Working + Episodic + Semantic + 测试 |
| **10** | Code Agent | 代码分析/修改/测试闭环 + artifact diff |
| **11** | Workflow Graph | DAG 定义/执行/条件边/checkpoint |
| **12** | Multi-Agent | Supervisor + Debate + Pipeline |
| **13** | RAG / Knowledge Base | 文档加载/切分/检索/引用 |
| **14** | Skill System | Skill 加载/检索/使用/评估 |
| **15** | Evaluation Harness | 5 层 benchmark + 指标报表 |
| **16** | Docs / Examples / Release | 完整文档 + 5 个可运行样例 + v0.1 release |

---

## 14. MVP 范围 (v0.1)

Phase 1-8 构成 MVP，必须具备：

- [x] 所有核心 schema（types.py）
- [x] ModelProvider: DeepSeek + OpenAI-compatible
- [x] Tool System: read_file, write_file, list_directory, shell, search, calculator
- [x] PermissionPolicy: review / auto / yolo
- [x] EventLogger: JSONL 格式
- [x] Planner / Executor / Critic: ReAct 循环
- [x] RuntimeState / Checkpoint: resume 支持
- [x] CLI: init / chat / run / code 四个子命令
- [x] Toy eval: 10 个基础任务，pass_rate > 70%

---

## 15. 风险与限制

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 输出不稳定 | tool_call 参数格式错误 | 严格的参数校验 + retry + 结构化 prompt |
| 工具调用安全风险 | 恶意命令执行 | PermissionPolicy deny 列表 + sandbox 隔离 |
| memory 污染 | 错误信息被当作知识存储 | importance 评分 + 定期 consolidation |
| 长任务成本 | token 消耗过高 | context 压缩 + 中间摘要 + early stop |
| benchmark 适配复杂 | eval 难以跨框架对比 | 统一 EvalTask 接口 + 标准化指标 |
| 多 Agent 空转 | 对话循环无进展 | max_turns + critic 评估 + supervisor 干预 |

---

## 16. 设计中的关键决策

1. **不绑定 LangChain / LlamaIndex**：自研核心抽象，保持零强依赖
2. **ModelProvider 而非直接调用 API**：所有 LLM 调用走统一接口，切换模型只改配置
3. **ToolRegistry 而非硬编码**：工具可插拔，支持 MCP 等外部协议扩展
4. **PermissionPolicy 独立于 Tool**：权限逻辑集中管理，不分散在各工具实现中
5. **EventLogger 全覆盖**：所有行为可追踪，为 eval / debug / replay 提供基础
6. **Checkpoint 在 step 级别**：平衡精度和存储开销
7. **Memory 分层**：Working / Episodic / Semantic / Procedural / Reflection 各司其职
8. **MVP 先做单 Agent**：Multi-Agent / Workflow 在 Phase 11-12 再做，避免早期过度设计
