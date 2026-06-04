# Observability

## 为什么 Agent 需要 Event Log

Agent 执行是多步、非线性、可能出错的。没有日志时：
- 出错了不知道哪一步失败
- 无法复现 bug
- 无法对比不同策略的效果
- 长任务中断后无法恢复

EvoAgent 的 observability 系统记录每一次 LLM 调用、Tool 执行、文件修改和状态变更。

## 核心概念

### run_id / step_id

- **run_id**: 一次 Agent 执行的唯一标识，从任务开始到结束
- **step_id**: PlanStep 的唯一标识，一个 run 包含多个 step

### events.jsonl 格式

每行一个 JSON 对象（JSONL）：

```json
{"id":"evt_abc","run_id":"run_xyz","step_id":"step_1","timestamp":"2025-...","event_type":"tool_call_started","payload":{"tool":"read_file","args":{"path":"main.py"}},"metadata":{}}
```

支持 17 种 event_type（定义在 `EventType` 枚举中）。

## Trace 目录结构

```
.runs/
  <run_id>/
    events.jsonl        # 所有事件
    state.json          # 当前 RuntimeState
    final_result.json   # AgentResult
    metadata.json        # 运行元数据
    patches/             # 文件 diff
    artifacts/           # 产生的文件
```

## Checkpoint 和 Resume

`CheckpointManager` 在 `.evoagent/checkpoints/<run_id>/` 下保存 `RuntimeState` 快照：

```
checkpoints/
  <run_id>/
    chk_xxx_before_edit.json   # 命名 checkpoint
    chk_yyy.json                # 自动 checkpoint
    latest.json                 # 最新 checkpoint 指针
```

恢复流程：
1. `load_checkpoint(run_id)` → 获取最新 checkpoint
2. 从 checkpoint.state 恢复 RuntimeState
3. 继续执行

## 文件 Diff 记录

`DiffRecorder` 在文件修改时生成 unified diff：

```
patches/step_1_main.py.patch
```

diff 内容使用标准 `---/+++` 格式，可读、可应用。

## 调试失败 run

```python
from evoagent.logging import JSONLEventLogger, EventType

logger = JSONLEventLogger(".runs/run_xxx/events.jsonl")

# 只看错误
errors = logger.get_events(event_type=EventType.ERROR)

# 看所有 tool 调用
tools = logger.get_events(event_type=EventType.TOOL_CALL_FINISHED)

# 重建状态
from evoagent.core.state import RuntimeState
state = RuntimeState.load_json(".runs/run_xxx/state.json")
```

## 后续集成

- **OpenTelemetry**: 将 Event 转为 OTel span，接入 Jaeger/Zipkin
- **Langfuse**: 导出 events.jsonl 到 Langfuse 进行 LLM 调用分析
- **Streaming**: 实时推送 event 到 WebSocket/回调
