"""Tool view — render individual tool call results."""


def render_tool_start(name: str, args: dict) -> str:
    short_args = ", ".join(f"{k}={str(v)[:30]}" for k, v in list(args.items())[:2])
    return f"◐ {name}({short_args})"


def render_tool_done(name: str, output: str, success: bool = True) -> str:
    prefix = "●" if success else "✗"
    short = output[:120].replace("\n", " ")
    return f"{prefix} {name}\n  {short}"


def render_tool_failed(name: str, error: str) -> str:
    return f"✗ {name}\n  {error[:120]}"
