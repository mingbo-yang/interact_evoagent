"""Configuration loader — YAML + environment variable overrides.

Reads default config from the evoagent package, with user overrides
from a local evoagent.yaml file. Environment variables take highest priority.
"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import ValidationError

from evoagent.config.schema import EvoAgentConfig

load_dotenv()

_DEFAULT_YAML: str | None = None

# Locate the default.yaml shipped with the package
try:
    from importlib.resources import files
    _default_path = files("evoagent.config") / "default.yaml"
    if _default_path.exists():
        _DEFAULT_YAML = str(_default_path)
except Exception:
    pass
# Fallback: look relative to this file
if _DEFAULT_YAML is None:
    _fallback = Path(__file__).parent / "default.yaml"
    if _fallback.exists():
        _DEFAULT_YAML = str(_fallback)


def _env_override(config: dict, prefix: str = "EVOAGENT_") -> dict:
    result = dict(config)
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        config_key = key[len(prefix):].lower()
        parts = config_key.split("__")
        if len(parts) < 2:
            continue
        target = result
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
    return result


def load_config(path: str | Path | None = None) -> EvoAgentConfig:
    """Load configuration from YAML file with environment overrides.

    Priority: user path > package default > error.

    Args:
        path: Optional user-provided config path. Falls back to package default.

    Returns:
        Validated EvoAgentConfig instance.

    Raises:
        FileNotFoundError: If no config file found.
        ValidationError: If the config fails Pydantic validation.
    """
    if path:
        config_path = Path(path)
    elif _DEFAULT_YAML:
        config_path = Path(_DEFAULT_YAML)
    else:
        raise FileNotFoundError(
            "No config file found. Run 'evoagent init' to create one, "
            "or pass a path to load_config()."
        )

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    raw = _env_override(raw)

    try:
        return EvoAgentConfig.model_validate(raw)
    except ValidationError:
        raise
