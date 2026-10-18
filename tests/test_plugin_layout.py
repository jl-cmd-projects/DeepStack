"""The published plugin keeps the slots a host install expects."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN = _ROOT / "plugins" / "deepstack"
_LAYOUT = (
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
    ".cursor-plugin/marketplace.json",
    "plugins/deepstack/.claude-plugin/plugin.json",
    "plugins/deepstack/.codex-plugin/plugin.json",
    "plugins/deepstack/.cursor-plugin/plugin.json",
    "plugins/deepstack/.github/plugin/plugin.json",
    "plugins/deepstack/models.json",
    "plugins/deepstack/hooks/hooks.json",
    "plugins/deepstack/hooks/codex-hooks.json",
    "plugins/deepstack/hooks/copilot-hooks.json",
    "plugins/deepstack/hooks/cursor-hooks.json",
    "plugins/deepstack/hooks/session-start.sh",
    "plugins/deepstack/hooks/session-start.ps1",
    "plugins/deepstack/skills/deepstack-mode/SKILL.md",
    "plugins/deepstack/skills/deepstack-help/SKILL.md",
    "plugins/deepstack/skills/setup-deepstack/SKILL.md",
    "plugins/deepstack/skills/principle-outside-judge/SKILL.md",
)
_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def test_marketplace_and_plugin_slots_exist() -> None:
    for each_relative in _LAYOUT:
        assert (_ROOT / each_relative).is_file(), each_relative


def test_entry_skill_names_the_three_triggers() -> None:
    skill_text = (_PLUGIN / "skills" / "deepstack-mode" / "SKILL.md").read_text(encoding="utf-8")
    assert "DeepStack intake" in skill_text
    assert "DeepStack search leaf" in skill_text
    assert "DeepStack reproducible-check leaf" in skill_text


def test_references_do_not_cite_files_this_repository_does_not_contain() -> None:
    references = _PLUGIN / "skills" / "deepstack-mode" / "references"
    text = "\n".join(path.read_text(encoding="utf-8") for path in references.rglob("*.md"))
    assert "features-start-with-an-eval.md" not in text
    assert "search-before-acting" not in text
    assert "archiving-agent-config.md" not in text
    assert "ARCHIVE-MANIFEST.md" not in text
    assert "deepen_role_gate.py" not in text


def test_relative_markdown_links_stay_inside_the_repository() -> None:
    root = _ROOT.resolve()
    for path in _ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        for match in _LINK.finditer(path.read_text(encoding="utf-8")):
            target = match.group(1).split("#", 1)[0].strip()
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (path.parent / target).resolve()
            assert resolved.is_file(), f"{path.relative_to(root)} -> {target}"
            assert root == resolved or root in resolved.parents, target


def test_cursor_catalog_uses_its_own_session_hook() -> None:
    market = json.loads((_ROOT / ".cursor-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    entry = market["plugins"][0]
    assert entry["name"] == "deepstack"
    plugin_root = _ROOT / entry["source"]
    manifest = json.loads((plugin_root / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "deepstack"
    hooks_path = plugin_root / str(manifest["hooks"]).removeprefix("./")
    assert hooks_path.name == "cursor-hooks.json"
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    command = hooks["hooks"]["sessionStart"][0]["command"]
    assert "session-start.sh" in command
    assert command.endswith(" cursor")
    claude_hooks = (_PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8")
    assert "commandWindows" not in claude_hooks


def test_sheet_paths_cover_every_runtime() -> None:
    runtimes = (
        _PLUGIN / "skills" / "deepstack-mode" / "references" / "runtimes.md"
    ).read_text(encoding="utf-8")
    assert "deepstack-models.md" in runtimes
    assert "CLAUDE_CONFIG_DIR" in runtimes
    assert "CODEX_HOME" in runtimes
    assert "COPILOT_HOME" in runtimes
    assert "~/.cursor" in runtimes


def test_session_start_formats_each_runtime_and_honors_the_off_switch(tmp_path: Path) -> None:
    script = _PLUGIN / "hooks" / "session-start.sh"
    home = tmp_path / "home"
    home.mkdir()
    quoted_root = tmp_path / 'quote"dir'
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "CLAUDE_PLUGIN_ROOT": str(_PLUGIN),
            "COPILOT_PLUGIN_ROOT": str(quoted_root),
        }
    )

    claude = subprocess.run([script, "claude"], check=False, capture_output=True, text=True, env=env)
    assert claude.returncode == 0
    assert claude.stdout.startswith("DeepStack:")
    assert "\n" not in claude.stdout.strip()
    assert not claude.stdout.lstrip().startswith("{")

    cursor = subprocess.run([script, "cursor"], check=False, capture_output=True, text=True, env=env)
    assert cursor.returncode == 0
    cursor_payload = json.loads(cursor.stdout)
    assert str(_PLUGIN / "skills" / "deepstack-mode" / "SKILL.md") in cursor_payload["additional_context"]

    sheet = home / ".cursor" / "deepstack-models.md"
    sheet.parent.mkdir()
    sheet.write_text("# DeepStack model configuration\nsession hook: off\n", encoding="utf-8")
    silenced = subprocess.run([script, "cursor"], check=False, capture_output=True, text=True, env=env)
    assert silenced.returncode == 0
    assert silenced.stdout == ""

    copilot = subprocess.run([script, "copilot"], check=False, capture_output=True, text=True, env=env)
    assert copilot.returncode == 0
    copilot_payload = json.loads(copilot.stdout)
    assert 'quote"dir' in copilot_payload["additionalContext"]

    unknown = subprocess.run([script, "nope"], check=False, capture_output=True, text=True, env=env)
    assert unknown.returncode == 2
    assert unknown.stdout == ""


def test_windows_hook_passes_the_runtime_and_the_off_switch() -> None:
    codex_hooks = json.loads((_PLUGIN / "hooks" / "codex-hooks.json").read_text(encoding="utf-8"))
    command_windows = codex_hooks["hooks"]["SessionStart"][0]["hooks"][0]["commandWindows"]
    assert "session-start.ps1" in command_windows
    assert command_windows.endswith(" codex")
    script = (_PLUGIN / "hooks" / "session-start.ps1").read_text(encoding="utf-8")
    assert "session hook: off" in script
    assert "additional_context" in script
    assert "additionalContext" in script
    assert "unknown runtime" in script


def test_source_links_the_article_and_keeps_one_quote() -> None:
    source_text = (
        _PLUGIN / "skills" / "deepstack-mode" / "references" / "source.md"
    ).read_text(encoding="utf-8")
    assert "Felix Rieseberg" in source_text
    assert "how-to-be-more-ambitious-a-tutorial-for-humans-with-models" in source_text
    assert source_text.count("I want a deeper version of this task") == 1
