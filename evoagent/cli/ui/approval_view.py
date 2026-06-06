"""Approval widget using prompt_toolkit for arrow-key selection."""

from dataclasses import dataclass

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style


@dataclass
class ApprovalChoice:
    label: str
    value: str
    description: str = ""


APPROVAL_STYLE = Style.from_dict({
    "frame": "#5b6478",
    "title": "#7dd3fc bold",
    "cmd": "#e5e9f0",
    "selected": "bg:#2a3142 #7dd3fc bold",
    "normal": "#8b93a7",
    "desc": "#5b6478",
    "risk.low": "#86efac",
    "risk.medium": "#fcd34d",
    "risk.high": "#fca5a5 bold",
    "info": "#8b93a7",
})


async def prompt_approval(action: str, command: str, description: str = "",
                          risk: str = "medium") -> str:
    """Show an arrow-key navigable approval prompt.

    Returns 'yes', 'remember', or 'no'.
    """
    choices = [
        ApprovalChoice("Yes", "yes", "approve this action once"),
        ApprovalChoice("Yes, and don't ask again", "remember",
                       "skip future prompts for this pattern"),
        ApprovalChoice("No", "no", "deny and let the agent try another approach"),
    ]
    selected = [0]
    risk_key = risk if risk in ("low", "medium", "high") else "medium"

    def get_text():
        lines = [
            ("class:frame", "╭─ "),
            ("class:title", "Permission required"),
            ("class:frame", " " + "─" * max(2, 40 - len(action))),
            ("", "\n"),
            ("class:frame", "│  "),
            ("class:title", action),
            ("class:frame", "   ["),
            (f"class:risk.{risk_key}", f"{risk_key} risk"),
            ("class:frame", "]\n"),
            ("class:frame", "│  "),
            ("class:cmd", command[:72]),
            ("", "\n"),
        ]
        if description:
            lines += [("class:frame", "│  "),
                      ("class:desc", description[:72]), ("", "\n")]
        lines.append(("class:frame", "│\n"))
        for i, c in enumerate(choices):
            sel = i == selected[0]
            prefix = "│  ❯ " if sel else "│    "
            style = "class:selected" if sel else "class:normal"
            lines.append(("class:frame", prefix))
            lines.append((style, f"{i + 1}. {c.label}"))
            lines.append(("class:desc", f"   {c.description}"))
            lines.append(("", "\n"))
        lines.append(("class:frame", "╰" + "─" * 44))
        return lines

    kb = KeyBindings()
    done = [None]

    @kb.add("up")
    def _up(event):
        selected[0] = (selected[0] - 1) % len(choices)

    @kb.add("down")
    def _down(event):
        selected[0] = (selected[0] + 1) % len(choices)

    @kb.add("1")
    @kb.add("2")
    @kb.add("3")
    def _number(event):
        num = int(event.data)
        selected[0] = num - 1
        done[0] = choices[num - 1].value
        event.app.exit()

    @kb.add("enter")
    def _enter(event):
        done[0] = choices[selected[0]].value
        event.app.exit()

    @kb.add("escape")
    def _esc(event):
        done[0] = "no"
        event.app.exit()

    @kb.add("c-c")
    def _ctrl_c(event):
        done[0] = "no"
        event.app.exit()

    content = Window(content=FormattedTextControl(get_text), always_hide_cursor=False)
    app = Application(layout=Layout(HSplit([content])), key_bindings=kb,
                      style=APPROVAL_STYLE, full_screen=False)

    await app.run_async()
    return done[0] or "no"


def render_approval(action: str, command: str, description: str = "",
                    risk: str = "medium"):
    """Backward compatibility wrapper for approval UI rendering."""
    return {"action": action, "command": command, "description": description, "risk": risk}


def get_approval_choice(prompt) -> str:
    """Backward compatibility wrapper for approval UI choice handling."""
    # Prompt object from legacy UI is not supported here.
    # Use prompt_approval directly instead for current interactive flows.
    raise NotImplementedError("Use prompt_approval() instead of get_approval_choice()")
