"""PermissionPolicy — deny > ask > allow with review/auto/yolo modes."""

import fnmatch
import re
from typing import Any

from evoagent.sandbox.schema import (
    PermissionDecision,
    PermissionMode,
    PermissionRule,
    PolicyConfig,
)

# Default deny rules — always enforced regardless of mode
_DEFAULT_DENY_RULES: list[PermissionRule] = [
    PermissionRule(action_type="shell", pattern="rm -rf*", decision=PermissionDecision.DENY,
                   description="Destructive deletion"),
    PermissionRule(action_type="shell", pattern="sudo*", decision=PermissionDecision.DENY,
                   description="Privilege escalation"),
    PermissionRule(action_type="shell", pattern="shutdown*", decision=PermissionDecision.DENY,
                   description="System shutdown"),
    PermissionRule(action_type="shell", pattern="reboot*", decision=PermissionDecision.DENY,
                   description="System reboot"),
    PermissionRule(action_type="shell", pattern="mkfs*", decision=PermissionDecision.DENY,
                   description="Filesystem formatting"),
    PermissionRule(action_type="shell", pattern="dd if=*", decision=PermissionDecision.DENY,
                   description="Raw disk write"),
    PermissionRule(action_type="shell", pattern="chmod -R*", decision=PermissionDecision.DENY,
                   description="Recursive permission change"),
    PermissionRule(action_type="shell", pattern="chown -R*", decision=PermissionDecision.DENY,
                   description="Recursive ownership change"),
    PermissionRule(action_type="shell", pattern="git push*", decision=PermissionDecision.DENY,
                   description="Force push to remote"),
    PermissionRule(action_type="shell", pattern="* | bash", decision=PermissionDecision.DENY,
                   match_type="glob", description="Pipe to bash (curl/wget)"),
    PermissionRule(action_type="file_write", pattern="/etc/*", decision=PermissionDecision.DENY,
                   description="Write to system config"),
    PermissionRule(action_type="file_write", pattern="/usr/*", decision=PermissionDecision.DENY,
                   description="Write to system binaries"),
    PermissionRule(action_type="file_write", pattern="/bin/*", decision=PermissionDecision.DENY,
                   description="Write to system binaries"),
]

# Default ask rules
_DEFAULT_ASK_RULES: list[PermissionRule] = [
    PermissionRule(action_type="shell", pattern="*install*", decision=PermissionDecision.ASK,
                   description="Package installation"),
    PermissionRule(action_type="shell", pattern="*uninstall*", decision=PermissionDecision.ASK,
                   description="Package removal"),
    PermissionRule(action_type="shell", pattern="*commit*", decision=PermissionDecision.ASK,
                   description="Git commit"),
]

# Default allow rules
_DEFAULT_ALLOW_RULES: list[PermissionRule] = [
    PermissionRule(action_type="shell", pattern="ls*", decision=PermissionDecision.ALLOW),
    PermissionRule(action_type="shell", pattern="echo*", decision=PermissionDecision.ALLOW),
    PermissionRule(action_type="shell", pattern="cat*", decision=PermissionDecision.ALLOW),
    PermissionRule(action_type="shell", pattern="grep*", decision=PermissionDecision.ALLOW),
    PermissionRule(action_type="shell", pattern="find*", decision=PermissionDecision.ALLOW),
    PermissionRule(action_type="shell", pattern="git status*", decision=PermissionDecision.ALLOW),
    PermissionRule(action_type="shell", pattern="git diff*", decision=PermissionDecision.ALLOW),
    PermissionRule(action_type="shell", pattern="git log*", decision=PermissionDecision.ALLOW),
    PermissionRule(action_type="file_read", pattern="*", decision=PermissionDecision.ALLOW),
    PermissionRule(action_type="file_write", pattern="*", decision=PermissionDecision.ALLOW),
    PermissionRule(action_type="python", pattern="*", decision=PermissionDecision.ALLOW),
    PermissionRule(action_type="git", pattern="*", decision=PermissionDecision.ALLOW),
]


class PermissionPolicy:
    """Central permission policy with deny > ask > allow priority.

    Modes:
    - review: every action must be confirmed (fallback = ask)
    - auto: low-risk actions auto-allowed, medium/high asked
    - yolo: everything allowed except deny rules

    Priority chain:
    deny > ask > allow > fallback (mode-dependent)
    """

    def __init__(self, config: PolicyConfig | None = None):
        """Initialize the policy.

        Args:
            config: PolicyConfig with mode and custom rules.
        """
        self.mode = config.mode if config else PermissionMode.AUTO
        self._deny_rules: list[PermissionRule] = list(_DEFAULT_DENY_RULES)
        self._ask_rules: list[PermissionRule] = list(_DEFAULT_ASK_RULES)
        self._allow_rules: list[PermissionRule] = list(_DEFAULT_ALLOW_RULES)

        # Merge user-provided rules
        if config:
            for rule in config.deny:
                self._deny_rules.append(rule)
            for rule in config.ask:
                self._ask_rules.append(rule)
            for rule in config.allow:
                self._allow_rules.append(rule)

    def _match(self, action_type: str, target: str, rules: list[PermissionRule]) -> bool:
        """Check if any rule matches the action.

        Supports three match types:
        - exact: target == pattern
        - glob: fnmatch (default, backward compatible)
        - regex: Python re.search

        For shell actions, uses token-aware matching to avoid
        false positives like '*install*' matching 'uninstall'.
        """
        for rule in rules:
            if rule.action_type != action_type:
                continue
            match_type = getattr(rule, "match_type", "glob") or "glob"
            if match_type == "exact":
                if target.strip() == rule.pattern.strip():
                    return True
            elif match_type == "regex":
                try:
                    if re.search(rule.pattern, target):
                        return True
                except re.error:
                    continue
            else:  # glob (default)
                # Token-aware match for shell commands: split by whitespace
                # so '*install*' matches 'pip install x' but not 'uninstall x'
                if action_type == "shell":
                    tokens = target.split()
                    for token in tokens:
                        if fnmatch.fnmatch(token, rule.pattern):
                            return True
                    # Also try whole-command match for patterns with spaces
                    if " " in rule.pattern:
                        if fnmatch.fnmatch(target, rule.pattern):
                            return True
                else:
                    if fnmatch.fnmatch(target, rule.pattern):
                        return True
        return False

    def check(
        self,
        action_type: str,
        target: str,
        risk_level: str = "low",
        metadata: dict[str, Any] | None = None,
    ) -> PermissionDecision:
        """Check whether an action is allowed.

        Args:
            action_type: file_read, file_write, shell, python, git.
            target: The command string or file path being checked.
            risk_level: low, medium, high.
            metadata: Optional extra info.

        Returns:
            PermissionDecision: allow, ask, or deny.
        """
        # 1. Deny rules have absolute priority
        if self._match(action_type, target, self._deny_rules):
            return PermissionDecision.DENY

        # 2. Ask rules
        if self._match(action_type, target, self._ask_rules):
            return PermissionDecision.ASK

        # 3. Allow rules
        if self._match(action_type, target, self._allow_rules):
            return PermissionDecision.ALLOW

        # 4. Fallback: mode-dependent
        if self.mode == PermissionMode.YOLO:
            return PermissionDecision.ALLOW

        if self.mode == PermissionMode.REVIEW:
            return PermissionDecision.ASK

        # AUTO mode
        if risk_level == "low":
            return PermissionDecision.ALLOW
        return PermissionDecision.ASK

    def is_denied(self, action_type: str, target: str) -> bool:
        """Check if an action is denied outright."""
        return self.check(action_type, target) == PermissionDecision.DENY
