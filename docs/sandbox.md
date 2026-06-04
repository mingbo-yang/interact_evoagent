# Sandbox 与 PermissionPolicy

## 为什么需要 Sandbox

Agent 在执行任务时可能：
- 执行任意 shell 命令
- 读写文件系统
- 运行 Python 代码
- 操作 Git 仓库

没有安全边界时，Agent 可能意外删除文件、泄露数据或执行恶意命令。

## PermissionPolicy 三层模式

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| **review** | 每个操作都需要人工确认 (fallback=ask) | 不可信任务、首次使用 |
| **auto** | low-risk 自动允许，medium/high 询问 (默认) | 交互式开发 |
| **yolo** | 全部允许（deny 规则仍生效） | 可信沙箱、CI/CD |

## 优先级链

```
deny > ask > allow > fallback (mode-dependent)
```

deny 规则**永远生效**，无论什么模式。包括：

- `rm -rf` — 破坏性删除
- `sudo` — 特权提升
- `shutdown` / `reboot` — 系统关机
- `mkfs` / `dd if=` — 文件系统格式化
- `chmod -R` / `chown -R` — 递归权限修改
- `git push` — 推送到远程
- `curl | bash` / `wget | bash` — 管道执行
- 写入 `/etc/` `/usr/` `/bin/`

## 配置权限规则

`evoagent/config/default.yaml`:

```yaml
permissions:
  mode: auto
  deny:
    - { action: shell, pattern: "rm -rf*", decision: deny }
    - { action: file_write, pattern: "/etc/*", decision: deny }
  ask:
    - { action: shell, pattern: "*install*", decision: ask }
  allow:
    - { action: shell, pattern: "echo*", decision: allow }
    - { action: file_read, pattern: "*", decision: allow }
```

### 规则匹配

使用 `fnmatch` 通配符匹配：
- `*` 匹配任意字符
- `action` 字段：shell, file_read, file_write, python, git

## Workspace 安全边界

`Workspace` 类确保所有文件操作在指定根目录内：

- `resolve_path(path)` — 解析路径并校验不越界
- `assert_inside_workspace(path)` — 越界时抛出 PermissionError
- `relative_path(path)` — 返回相对路径

`../` 遍历和符号链接都会被 `Path.resolve()` 消除，然后校验。

## LocalSandbox

当前唯一完整实现的 Sandbox：

- `run_shell(command, cwd, timeout)` — 执行 shell 命令
- `run_python(code, script_path, timeout)` — 执行 Python 代码
- `read_file(path)` — 读取文件（自动 workspace 校验）
- `write_file(path, content, overwrite)` — 写入文件

所有操作都先经过 `PermissionPolicy.check()`。

## DockerSandbox（后续）

预留接口，后续 Phase 将实现：

- 隔离的文件系统
- 网络控制
- 资源限制 (CPU/memory)
- 基于镜像的环境 (python:3.11-slim 等)

## 工具与 Sandbox 集成

`BashTool` 和 `PythonTool` 接受可选的 `sandbox` 参数：

```python
from evoagent.sandbox import LocalSandbox, Workspace, PermissionPolicy

ws = Workspace("/path/to/project")
policy = PermissionPolicy()
sandbox = LocalSandbox(workspace=ws, policy=policy)

tool = BashTool(workspace=ws.root, sandbox=sandbox)
result = await tool.run(command="echo hello")
```

如果未提供 sandbox，工具回退到直接 subprocess 调用（向后兼容 Phase 4 测试）。
