# Skills

Agent skills shared by every agent harness (Claude Code, Codex, OpenCode, Pi). Each folder is
one skill with a `SKILL.md`.

- `codebase-cleanup`: map a repo's strategy and architecture, then simplify it without changing behaviour.
- `frontend-design`: distinctive, intentional visual design for new or reshaped UI.
- `hexagonal-architecture`: design, assess or migrate a codebase to ports and adapters with DDD, dependency injection and fakes over mocks.
- `privacy-check`: privacy and security gate for apps that hold user data, before merging or deploying.
- `security-audit`: inspect software for malicious behaviour, telemetry and supply-chain risk before installing it.
- `strategic-coding`: approach every coding task strategically: the real need or root cause, related code, fit with the codebase's direction, and leaving it easier to change.

This repo is public. Keep anything personal (hostnames, addresses, usernames, private projects)
out of it.

## Install

```bash
git clone https://github.com/n0mahd/skills.git ~/Skills
```

Then link each folder into your harness's skills directory (for example
`ln -s ~/Skills/privacy-check ~/.claude/skills/`).
