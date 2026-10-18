#!/bin/sh
set -eu
runtime="${1:-}"
case "$runtime" in
  claude)
    root="${CLAUDE_PLUGIN_ROOT:?}"
    sheet="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/deepstack-models.md"
    ;;
  codex)
    root="${CLAUDE_PLUGIN_ROOT:?}"
    sheet="${CODEX_HOME:-$HOME/.codex}/deepstack-models.md"
    ;;
  copilot)
    root="${COPILOT_PLUGIN_ROOT:?}"
    sheet="${COPILOT_HOME:-$HOME/.copilot}/deepstack-models.md"
    ;;
  cursor)
    root="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
    sheet="${HOME}/.cursor/deepstack-models.md"
    ;;
  *)
    echo "session-start.sh: unknown runtime '${runtime}'" >&2
    exit 2
    ;;
esac
if [ -f "$sheet" ] && grep -qx 'session hook: off' "$sheet"; then
  exit 0
fi
mandate="DeepStack: on a first task, read ${root}/skills/deepstack-mode/SKILL.md and follow it."
if [ "$runtime" = copilot ]; then
  printf '%s\n' "{\"additionalContext\": \"${mandate}\"}"
else
  printf '%s\n' "$mandate"
fi
