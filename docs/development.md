# EvoAgent 开发指南

## 环境准备

```bash
# 克隆仓库后
cd agent

# 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate

# 安装开发依赖
pip install -e ".[dev]"
```

## 配置 API Key

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入你的 DeepSeek API Key
# DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

**注意**: 不要把真实 API Key 提交到 Git。`.env` 已在 `.gitignore` 中。

## 运行测试

```bash
pytest                          # 运行所有测试
pytest tests/test_imports.py    # 运行特定文件
pytest -x                       # 遇错即停
pytest --tb=long                # 详细回溯
```

## 代码检查

```bash
ruff check .                    # 检查代码风格
ruff check --fix .              # 自动修复
ruff format .                   # 格式化代码
```

## 类型检查

```bash
mypy evoagent                   # 检查类型标注
```

## 编译验证

```bash
python -m compileall evoagent   # 验证所有模块可编译
```

## 全部检查（提交前）

```bash
python -m compileall evoagent && ruff check . && pytest && mypy evoagent
```

## 贡献规则

1. **不要硬编码 API Key** — 始终从环境变量或配置读取
2. **每个模块必须有类型标注和 docstring**
3. **新功能必须有对应测试**
4. **不要引入不必要的依赖**
5. **保持模块解耦** — 通过抽象基类扩展，不 monkey-patch
6. **先读设计文档** — `docs/design.md` 描述模块边界和接口约定

## 目录约定

```
evoagent/<module>/__init__.py   # 模块入口，导出公开 API
evoagent/<module>/base.py       # 抽象基类（如有）
tests/test_<module>.py          # 测试文件（镜像 src 结构）
```
