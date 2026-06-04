# DeepSeek 接入指南

## 配置 API Key

EvoAgent 从环境变量 `DEEPSEEK_API_KEY` 读取 API Key。

```bash
# 方式一：直接导出
export DEEPSEEK_API_KEY="sk-your-key-here"

# 方式二：.env 文件
echo "DEEPSEEK_API_KEY=sk-your-key-here" >> .env
```

**永远不要把 API Key 写进代码、配置文件或提交到 Git。**

## 可用模型

| 模型 | 用途 | 说明 |
|------|------|------|
| `deepseek-chat` | 通用对话、工具调用 | 默认 executor 模型，适合快速执行 |
| `deepseek-reasoner` | 推理、规划、评估 | 默认 planner/critic 模型，适合复杂推理 |

## 配置不同角色使用不同模型

`evoagent/config/default.yaml` 中已预设：

```yaml
models:
  planner:
    provider: deepseek
    model: deepseek-reasoner     # 规划用推理模型
  executor:
    provider: deepseek
    model: deepseek-chat         # 执行用快速模型
  critic:
    provider: deepseek
    model: deepseek-reasoner     # 评估用推理模型
  summarizer:
    provider: deepseek
    model: deepseek-chat
  default:
    provider: deepseek
    model: deepseek-chat         # 默认回退
```

环境变量覆盖：

```bash
# 单独修改 planner 的模型
export EVOAGENT_MODELS__PLANNER__MODEL="deepseek-chat"
```

## 为什么 Agent 主流程不能直接调用 API

EvoAgent 的设计原则是 **model-agnostic**（模型无关）。Agent 主流程只依赖 `BaseLLMProvider` 抽象接口：

```python
# ✅ 正确：通过抽象接口
from evoagent.models import BaseLLMProvider
async def execute(provider: BaseLLMProvider, task: str): ...

# ❌ 错误：硬编码具体实现
from openai import OpenAI
client = OpenAI(api_key="sk-xxx")  # 换模型要改代码
```

这样做的好处：

1. **换模型不改代码** — 从 DeepSeek 切换到 OpenAI 只需改配置文件
2. **可测试** — 测试中用 `MockLLMProvider`，不需要真实 API
3. **可对比** — 同一任务可以用不同模型跑，对比效果
4. **可扩展** — 新增 LiteLLM、本地模型只需实现 `BaseLLMProvider`

## 接入其他 OpenAI-compatible 模型

任何兼容 OpenAI `/v1/chat/completions` 的 API 都可以通过 `openai_compatible` provider 接入：

```yaml
models:
  default:
    provider: openai_compatible
    model: your-model-name
    base_url: https://your-api.example.com/v1
    api_key_env: YOUR_API_KEY_ENV
```

支持的 provider：

| Provider | 说明 |
|----------|------|
| `deepseek` | DeepSeek API，自动设置默认值 |
| `openai_compatible` | 通用 OpenAI-compatible API |
| `mock` | 测试用，不发起网络请求 |
| `litellm` | 预留，暂未实现 |
