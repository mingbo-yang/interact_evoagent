"""prompt_toolkit PromptSession with a dynamic, polished prompt + toolbar."""

from collections.abc import Callable
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.application.current import get_app
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.utils import get_cwidth

from evoagent.cli.ui.completion import SlashCompleter

_MODE_COLORS = {"default": "#7dd3fc", "plan": "#fcd34d", "auto": "#c4b5fd"}

PROMPT_STYLE = Style.from_dict({
    "arrow": "#7dd3fc bold",
    "mode.default": "#7dd3fc bold",
    "mode.plan": "#fcd34d bold",
    "mode.auto": "#c4b5fd bold",
    "pad": "",
    # Pure, single-colour bottom toolbar: no rainbow accents, no wrapping.
    "bottom-toolbar": "bg:#1b1f2a #b8c0d4",
})


def _clip_to_width(text: str, width: int) -> str:
    """Clip text to display width, preserving a single-line toolbar."""
    if get_cwidth(text) <= width:
        return text
    out = ""
    for ch in text:
        if get_cwidth(out + ch + "…") > width:
            return out + "…"
        out += ch
    return out


def render_toolbar_text(model: str, status: str = "", width: int = 80) -> str:
    """Return a width-fitted, single-colour toolbar string."""
    width = max(20, width)
    # Prefer graceful degradation over a hard mid-word cutoff:
    # full -> no /help -> no status -> compact hints -> final ellipsis.
    candidates = [
        (28, True, "↑↓ history  ·  Enter send  ·  Esc Esc quit  ·  /help"),
        (24, True, "↑↓ history  ·  Enter send  ·  Esc Esc quit"),
        (24, True, "↑↓ history  ·  ↵ send  ·  esc esc"),
        (22, False, "↑↓ history  ·  ↵ send  ·  esc esc"),
        (18, False, "↑↓ · ↵ · esc"),
        (18, False, ""),
    ]
    text = ""
    for model_w, include_status, hints in candidates:
        model_part = _clip_to_width(model, model_w)
        text = f"  model {model_part}"
        if include_status and status:
            text += f"  ·  {status}"
        if hints:
            text += f"  ·  {hints}"
        if get_cwidth(text) <= width:
            break
    text = _clip_to_width(text, width)
    return text + " " * max(0, width - get_cwidth(text))


def create_prompt_session(
    get_mode: Callable[[], str] | None = None,
    get_model: Callable[[], str] | None = None,
    get_status: Callable[[], str] | None = None,
    history_path: str = ".evoagent/history",
    *,
    mode: str = "default",
    model_label: str = "deepseek:chat",
    bottom_text: str = "",
) -> PromptSession:
    """Create the interactive prompt.

    Prefer the ``get_*`` callables so the prompt and toolbar reflect live state
    (mode / model / context) without recreating the session. The static
    ``mode`` / ``model_label`` / ``bottom_text`` keyword arguments remain
    supported for backward compatibility.
    """
    _mode = get_mode or (lambda: mode)
    _model = get_model or (lambda: model_label)
    _status = get_status or (lambda: bottom_text)

    def _message():
        m = _mode()
        cls = f"class:mode.{m}" if m in _MODE_COLORS else "class:mode.default"
        # Column-0 prompt: a single mode-coloured arrow marks each user turn so
        # the input and the assistant reply share the same left edge.
        return [(cls, "❯ ")]

    def _toolbar():
        try:
            width = get_app().output.get_size().columns
        except Exception:
            width = 80
        return [("class:bottom-toolbar",
                 render_toolbar_text(_model(), _status(), width))]

    bindings = KeyBindings()

    @bindings.add("tab")
    def _tab(event):
        event.app.current_buffer.complete_next()

    @bindings.add("up")
    def _up(event):
        """Browse backward through input history."""
        event.current_buffer.history_backward()

    @bindings.add("down")
    def _down(event):
        """Browse forward through input history."""
        event.current_buffer.history_forward()

    @bindings.add("enter")
    def _enter(event):
        event.app.current_buffer.validate_and_handle()

    @bindings.add("escape", "enter")
    def _esc_enter(event):
        event.app.current_buffer.insert_text("\n")

    @bindings.add("c-j")
    def _cj(event):
        event.app.current_buffer.insert_text("\n")

    @bindings.add("c-d")
    def _cd(event):
        if not event.app.current_buffer.text:
            event.app.exit(result="/exit")
        else:
            event.app.current_buffer.cut_right()

    @bindings.add("c-o")
    def _co(event):
        event.app.exit(result="/toggle_verbose")

    @bindings.add("escape")
    def _esc(event):
        event.app.exit(result="/escape")

    @bindings.add("c-c")
    def _cc(event):
        if event.app.current_buffer.text:
            event.app.current_buffer.text = ""
        else:
            event.app.exit(result="/interrupt")

    try:
        Path(history_path).parent.mkdir(parents=True, exist_ok=True)
        history = FileHistory(history_path)
    except Exception:
        history = None

    return PromptSession(
        message=_message, style=PROMPT_STYLE, completer=SlashCompleter(),
        key_bindings=bindings, history=history, multiline=False,
        wrap_lines=False, bottom_toolbar=_toolbar,
    )
