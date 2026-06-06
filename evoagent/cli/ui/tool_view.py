"""Tool view — render individual tool call results (plain-text helpers)."""

from evoagent.cli.ui.symbols import sym


def render_tool_start(name: str, args: dict) -> str:
    short_args = ", ".join(f"{k}={str(v)[:30]}" for k, v in list(args.items())[:2])
    return f"{sym('running')} {name}({short_args})"


def render_tool_done(name: str, output: str, success: bool = True) -> str:
    prefix = sym("ok") if success else sym("fail")
    short = output[:120].replace("\n", " ")
    return f"{prefix} {name}\n  {short}"


def render_tool_failed(name: str, error: str) -> str:
    return f"{sym('fail')} {name}\n  {error[:120]}"
