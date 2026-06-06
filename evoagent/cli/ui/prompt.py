"""prompt_toolkit PromptSession with keybindings, history, and bottom toolbar."""

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from evoagent.cli.ui.completion import SlashCompleter

PROMPT_STYLE = Style.from_dict({
    "prompt": "#7dd3fc bold",
    "mode": "#fcd34d",
    "model": "#8b93a7",
    "separator": "#7dd3fc bold",
    "bracket": "#5b6478",
    "toolbar": "bg:#1f2430 #8b93a7",
    "toolbar.accent": "bg:#1f2430 #7dd3fc",
})


def create_prompt_session(mode: str = "default", model_label: str = "deepseek:chat",
                          history_path: str = ".evoagent/history",
                          bottom_text: str = "") -> PromptSession:
    mode_colors = {"default": "#7dd3fc", "plan": "#fcd34d", "auto": "#c4b5fd"}
    mode_color = mode_colors.get(mode, "#7dd3fc")

    prompt_text = [
        ("class:bracket", "  "),
        ("fg:" + mode_color + " bold", mode),
        ("class:bracket", " · "),
        ("class:model", model_label[:20]),
        ("class:separator", "  ❯ "),
    ]

    bindings = KeyBindings()

    @bindings.add("tab")
    def _tab(event):
        """Tab: trigger completion."""
        event.app.current_buffer.complete_next()

    @bindings.add("enter")
    def _enter(event):
        """Enter submits the input."""
        event.app.current_buffer.validate_and_handle()

    @bindings.add("escape", "enter")
    def _esc_enter(event):
        """Esc+Enter inserts newline."""
        event.app.current_buffer.insert_text("\n")

    @bindings.add("c-j")
    def _cj(event):
        """Ctrl+J inserts newline."""
        event.app.current_buffer.insert_text("\n")

    @bindings.add("c-d")
    def _cd(event):
        if not event.app.current_buffer.text:
            event.app.exit(result="/exit")
        else:
            # Delete forward on non-empty input
            event.app.current_buffer.cut_right()

    @bindings.add("c-o")
    def _co(event):
        """Ctrl+O: toggle verbose/compact."""
        event.app.exit(result="/toggle_verbose")

    @bindings.add("escape")
    def _esc(event):
        """Escape: routed through EscapeActionResolver."""
        # Let the CLI layer handle escape resolution
        event.app.exit(result="/escape")

    @bindings.add("c-c")
    def _cc(event):
        if event.app.current_buffer.text:
            event.app.current_buffer.text = ""
        else:
            event.app.exit(result="/interrupt")

    try:
        history = FileHistory(history_path)
    except Exception:
        history = None

    def _toolbar():
        text = bottom_text or f"{mode} · {model_label[:20]}"
        return [
            ("class:toolbar", "  "),
            ("class:toolbar", text),
            ("class:toolbar", "    "),
            ("class:toolbar", "↵ send"),
            ("class:toolbar", "   esc·esc quit"),
            ("class:toolbar", "   /help"),
        ]

    return PromptSession(
        message=prompt_text, style=PROMPT_STYLE, completer=SlashCompleter(),
        key_bindings=bindings, history=history, multiline=False,
        wrap_lines=False, bottom_toolbar=_toolbar,
    )
