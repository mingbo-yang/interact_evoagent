# EvoAgent 开发路线图

## 总体阶段

| Phase | 名称 | 目标 | 预计新增文件 |
|-------|------|------|-------------|
| 0 | 架构设计 | 完成 design.md、roadmap.md、README.md | 3 |
| 1 | 项目初始化 | pyproject.toml、目录骨架、ruff/pytest/mypy、CI | 10+ |
| 2 | Core Schema | 所有核心抽象类型定义 | 3-4 |
| 3 | EventLogger | JSONL 事件日志系统 | 2-3 |
| 4 | ModelProvider | LLM 抽象层 + DeepSeek 适配器 | 4-5 |
| 5 | Tool System | ToolRegistry + 基础工具 + ToolResult | 5-6 |
| 6 | PermissionPolicy | review/auto/yolo 三层权限 | 2-3 |
| 7 | Planner | 任务分解与计划生成 | 3-4 |
| 8 | Executor + Agent Runtime | 执行引擎 + ReAct 循环 | 3-4 |
| 9 | Critic + Reflector | 输出评估与策略反思 | 3-4 |
| 10 | Memory System | working/episodic/semantic/procedural/reflection | 6-8 |
| 11 | RuntimeState + Checkpoint | 状态持久化与任务恢复 | 3-4 |
| 12 | Workflow Graph | 节点/边/条件/人工中断 | 5-6 |
| 13 | RAG + Knowledge Base | 文档加载/切分/检索/引用 | 4-5 |
| 14 | Skill System | 技能注册/检索/评估 | 3-4 |
| 15 | Multi-Agent | supervisor/debate/pipeline | 4-5 |
| 16 | CLI + Eval + Docs | 命令行、评估基准、文档补全 | 10+ |

## Phase 1：项目初始化（详细）

### 目标
搭建可编译、可测试、可 lint 的工程骨架。

### 文件
```
pyproject.toml
evoagent/__init__.py
evoagent/config/__init__.py
evoagent/config/settings.py
tests/__init__.py
tests/conftest.py
tests/test_version.py
docs/design.md      (已存在)
docs/roadmap.md     (已存在)
README.md           (已存在)
```

### 验收标准
- [x] `python -m compileall evoagent` 通过
- [x] `pytest` 至少有 1 个测试通过
- [x] `ruff check .` 无错误
- [x] `pip install -e ".[dev]"` 可安装

## Phase 2：Core Schema（详细）

### 目标
定义所有核心抽象类型，后续所有模块基于这些类型构建。

### 新增类型
- Message, ToolCall, ToolResult
- LLMRequest, LLMResponse
- Plan, PlanStep
- RuntimeState, AgentResult
- Event
- MemoryItem
- WorkflowNode
- RoleAgent
- EvalTask, EvalResult

### 验收标准
- [x] 所有类型可 import
- [x] 所有类型有 docstring
- [x] 单元测试覆盖序列化/反序列化

## MVP（v0.1）范围

MVP 包含 Phase 0-9，即：
- 架构设计 ✓
- 项目骨架
- 核心类型
- 事件日志
- 模型提供商
- 工具系统
- 权限策略
- 规划器
- 执行器 + Agent Runtime
- 评估器 + 反思器

发布标准：
- 能用 `evoagent run "任务描述"` 完成一个文件操作任务
- 能用 `evoagent code "需求"` 在沙箱中修改代码
- 有 5+ toy eval 用例，通过率 >= 80%
- 文档覆盖所有公开 API
