# Tool System

## 概述

EvoAgent 的工具系统提供统一接口来注册、发现和执行工具。所有工具返回标准化的 `ToolResult`，并且每个工具都有 Pydantic input_schema 用于参数校验和自动生成 OpenAI function-calling schema。

## BaseTool 抽象

每个工具必须实现：

```python
class BaseTool(ABC):
    name: str                    # 唯一标识符
    description: str             # 人类可读描述
    input_schema: type[BaseModel]  # Pydantic 参数模型
    output_schema: type[BaseModel] | None  # 可选输出模型
    risk_level: RiskLevel        # low / medium / high

    async def run(self, **kwargs) -> ToolResult: ...
```

`arun()` 是主入口，自动完成参数校验、计时、错误包装。

## ToolRegistry

```python
registry = ToolRegistry(workspace=Path("/path/to/workspace"))

# 注册
registry.register(ReadFileTool(workspace))

# 查询
tool = registry.get("read_file")

# 列出
registry.list_tools()  # ["bash", "edit_file", "grep", ...]

# 生成 LLM schema
registry.get_tool_schemas()  # OpenAI function-calling 格式

# 执行
result = await registry.run_tool("read_file", {"path": "main.py"})
```

## 内置工具

| 工具 | 风险 | 说明 |
|------|------|------|
| `read_file` | low | 读取工作区文件，支持行范围和字符截断 |
| `write_file` | medium | 写入文件，自动创建父目录，overwrite 开关 |
| `edit_file` | medium | 查找替换文本，默认要求 old_text 唯一 |
| `list_directory` | low | 列出目录，默认忽略 .git/__pycache__/.venv/node_modules |
| `grep` | low | 在工作区内搜索文本模式 |
| `bash` | high | 执行 shell 命令，30s 超时，阻止 rm -rf/sudo 等 |
| `python` | high | 执行 Python 代码或脚本 |
| `git_status` | low | git status --short |
| `git_diff` | low | git diff，支持 path 过滤 |

## 工具 Schema 规范

每个工具的 input_schema 是 Pydantic BaseModel：

```python
class ReadFileInput(BaseModel):
    path: str = Field(..., description="File path relative to workspace.")
    start_line: int | None = Field(default=None)
    end_line: int | None = Field(default=None)
    max_chars: int = Field(default=50000)
```

`to_openai_tool_schema()` 自动将此转化为：

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read a file from the workspace...",
    "parameters": { ... }
  }
}
```

## Workspace 安全边界

所有文件工具必须通过 `resolve_workspace_path()` 解析路径：

- 相对路径 → 拼接 workspace 根目录
- `Path.resolve()` 消除 `..` 和符号链接
- 解析后路径必须在 workspace 子树内，否则抛出 `PermissionError`
- 禁止通过 `../` 访问 workspace 外路径

## 如何新增自定义工具

```python
from pydantic import BaseModel, Field
from evoagent.tools.base import BaseTool, RiskLevel
from evoagent.tools.schema import ToolResult

class MyInput(BaseModel):
    query: str = Field(..., description="Search query.")

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful."
    input_schema = MyInput
    risk_level = RiskLevel.LOW

    def __init__(self, workspace):
        self.workspace = workspace

    async def run(self, query: str) -> ToolResult:
        # Your logic here
        return ToolResult(call_id="...", name=self.name, success=True, output="done")

# Register
registry.register(MyTool(workspace))
```

## 后续集成

### PermissionPolicy（Phase 5）

`BaseTool` 已预留 `permission_check` hook：

```python
tool.permission_check = lambda name, args: policy.allow(name, args)
```

### Sandbox（后续 Phase）

文件工具支持传入 workspace 参数，Sandbox 实现可提供隔离的文件系统。

### EventLogger（Phase 3）

`BaseTool` 已预留 `event_callback` hook，每次工具执行后触发。

### MCP 支持（后续 Phase）

MCP 工具适配器将实现 `BaseTool`，通过 ToolRegistry 统一注册。
