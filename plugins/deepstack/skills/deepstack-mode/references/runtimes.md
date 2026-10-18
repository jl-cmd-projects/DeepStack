# Runtimes

On Claude Code the skills use the Skill tool and the Agent tool as written. On Codex, Copilot, and Cursor, use that runtime's tool for reading a skill and spawning an agent. The steps stay the same. Model names come from the override sheet `/setup-deepstack` writes for that runtime.

The sheet file is `deepstack-models.md` in the runtime directory below.

| Runtime | Directory |
|---|---|
| Claude Code | `$CLAUDE_CONFIG_DIR`, or `~/.claude` when that variable is unset |
| Codex | `$CODEX_HOME`, or `~/.codex` when that variable is unset |
| Copilot | `$COPILOT_HOME`, or `~/.copilot` when that variable is unset |
| Cursor | `~/.cursor` |
