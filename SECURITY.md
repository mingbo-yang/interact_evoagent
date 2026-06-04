# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please do NOT open a public issue.
Contact the maintainers directly.

## API Keys

- Never commit API keys to the repository
- Always use environment variables for secrets
- `.env` is in `.gitignore`
- Tests use `MockLLMProvider` — zero real API calls

## Sandbox

EvoAgent's PermissionPolicy blocks dangerous commands by default:
- `rm -rf`, `sudo`, `shutdown`, `reboot`, `mkfs`
- `curl | bash`, `wget | bash`
- Writing to `/etc/`, `/usr/`, `/bin/`

Use `--mock` mode for safe testing without API keys.

## Docker Sandbox

When using DockerSandbox:
- Workspace is mounted read-write by default
- Network is disabled by default (`--network none`)
- All shell commands go through PermissionPolicy first

## Dependencies

- Keep dependencies minimal
- No binary execution from PyPI packages without review
- Prefer stdlib over external packages where possible
