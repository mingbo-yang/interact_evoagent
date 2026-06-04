"""Configuration schema — Pydantic models for type-safe config."""

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class PermissionMode(StrEnum):
    REVIEW = "review"
    AUTO = "auto"
    YOLO = "yolo"


class ProjectConfig(BaseModel):
    """Project-level settings."""

    name: str = "evoagent"
    version: str = "0.1.0"
    work_dir: Path = Path(".")


class SingleModelConfig(BaseModel):
    """Configuration for a single model provider instance."""

    provider: str = "deepseek"
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com/v1"
    api_key_env: str = "DEEPSEEK_API_KEY"
    temperature: float = 0.0
    max_tokens: int = 4096
    max_retries: int = 3
    timeout: int = 60
    input_price_per_1k: float = 0.0
    output_price_per_1k: float = 0.0


class ModelsConfig(BaseModel):
    """Per-role model provider settings.

    Each role (planner, executor, critic, summarizer, default)
    can use a different model. For example, planner/critic
    can use deepseek-reasoner while executor uses deepseek-chat.
    """

    planner: SingleModelConfig = Field(
        default_factory=lambda: SingleModelConfig(model="deepseek-reasoner"),
    )
    executor: SingleModelConfig = Field(default_factory=SingleModelConfig)
    critic: SingleModelConfig = Field(
        default_factory=lambda: SingleModelConfig(model="deepseek-reasoner"),
    )
    summarizer: SingleModelConfig = Field(default_factory=SingleModelConfig)
    default: SingleModelConfig = Field(default_factory=SingleModelConfig)


class RuntimeConfig(BaseModel):
    """Agent runtime limits."""

    max_turns: int = 20
    max_llm_calls: int = 50
    max_tool_calls: int = 100
    max_context_tokens: int = 128_000
    checkpoint_enabled: bool = True
    checkpoint_dir: Path = Path(".evoagent/checkpoints")


class PermissionRuleConfig(BaseModel):
    """A single permission rule."""

    action: str = Field(default="shell", description="Action type: shell, file_write, file_read, python, git.")
    pattern: str = Field(default="*", description="Pattern to match.")
    decision: str = Field(default="deny", description="Decision: allow, ask, deny.")
    description: str = Field(default="", description="Human-readable reason.")


class PermissionsConfig(BaseModel):
    """Permission policy settings."""

    mode: PermissionMode = PermissionMode.AUTO
    deny: list[PermissionRuleConfig] = Field(default_factory=list)
    ask: list[PermissionRuleConfig] = Field(default_factory=list)
    allow: list[PermissionRuleConfig] = Field(default_factory=list)


class SandboxConfig(BaseModel):
    """Sandbox execution settings."""

    type: str = Field(default="local", description="Sandbox type: local, docker.")
    timeout: int = Field(default=60, description="Default timeout in seconds.")
    workspace: Path = Field(default=Path("."), description="Workspace root directory.")


class WorkingMemoryConfig(BaseModel):
    enabled: bool = True
    max_items: int = 20


class EpisodicMemoryConfig(BaseModel):
    enabled: bool = True
    db_path: Path = Path(".evoagent/memory/episodic.jsonl")


class SemanticMemoryConfig(BaseModel):
    enabled: bool = False
    db_path: Path = Path(".evoagent/memory/semantic.jsonl")


class ProceduralMemoryConfig(BaseModel):
    enabled: bool = False
    db_path: Path = Path(".evoagent/memory/procedural.jsonl")


class ReflectionMemoryConfig(BaseModel):
    enabled: bool = False
    interval: int = 5


class MemoryConfig(BaseModel):
    """Memory subsystem settings."""

    working: WorkingMemoryConfig = Field(default_factory=WorkingMemoryConfig)
    episodic: EpisodicMemoryConfig = Field(default_factory=EpisodicMemoryConfig)
    semantic: SemanticMemoryConfig = Field(default_factory=SemanticMemoryConfig)
    procedural: ProceduralMemoryConfig = Field(default_factory=ProceduralMemoryConfig)
    reflection: ReflectionMemoryConfig = Field(default_factory=ReflectionMemoryConfig)


class LoggingConfig(BaseModel):
    """Event logging settings."""

    enabled: bool = True
    traces_dir: Path = Path(".runs")
    save_checkpoints: bool = True
    save_diffs: bool = True
    log_dir: Path = Path(".evoagent/logs")
    log_format: Literal["jsonl"] = "jsonl"
    include_tool_results: bool = True
    include_llm_responses: bool = True


class SkillsConfig(BaseModel):
    """Skill system settings."""

    enabled: bool = True
    paths: list[Path] = Field(default_factory=lambda: [Path("evoagent/skills/builtin")])
    top_k: int = 3
    usage_path: Path = Path(".evoagent/skills_usage.json")


class RagConfig(BaseModel):
    """RAG / Knowledge Base settings."""

    enabled: bool = False
    paths: list[Path] = Field(default_factory=list)
    chunk_size: int = 1000
    chunk_overlap: int = 100
    top_k: int = 5
    retriever: str = "keyword"


class EvalConfig(BaseModel):
    """Evaluation settings."""

    benchmark_dir: Path = Path("benchmarks/")
    output_dir: Path = Path(".evoagent/eval_results")


class EvoAgentConfig(BaseModel):
    """Top-level EvoAgent configuration."""

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    permissions: PermissionsConfig = Field(default_factory=PermissionsConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    rag: RagConfig = Field(default_factory=RagConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    eval: EvalConfig = Field(default_factory=EvalConfig)
