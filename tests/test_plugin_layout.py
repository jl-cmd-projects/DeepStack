"""The published plugin keeps the slots a host install expects."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN = _ROOT / "plugins" / "deepstack"
_LAYOUT = (
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
    "plugins/deepstack/.claude-plugin/plugin.json",
    "plugins/deepstack/.codex-plugin/plugin.json",
    "plugins/deepstack/.github/plugin/plugin.json",
    "plugins/deepstack/models.json",
    "plugins/deepstack/hooks/hooks.json",
    "plugins/deepstack/hooks/codex-hooks.json",
    "plugins/deepstack/hooks/copilot-hooks.json",
    "plugins/deepstack/hooks/session-start.sh",
    "plugins/deepstack/skills/deepstack-mode/SKILL.md",
    "plugins/deepstack/skills/deepstack-help/SKILL.md",
    "plugins/deepstack/skills/setup-deepstack/SKILL.md",
    "plugins/deepstack/skills/principle-outside-judge/SKILL.md",
)


def test_marketplace_and_plugin_slots_exist() -> None:
    for each_relative in _LAYOUT:
        assert (_ROOT / each_relative).is_file(), each_relative


def test_entry_skill_names_the_three_triggers() -> None:
    skill_text = (_PLUGIN / "skills" / "deepstack-mode" / "SKILL.md").read_text(encoding="utf-8")
    assert "DeepStack intake" in skill_text
    assert "DeepStack search leaf" in skill_text
    assert "DeepStack reproducible-check leaf" in skill_text


def test_session_start_accepts_cursor() -> None:
    script_text = (_PLUGIN / "hooks" / "session-start.sh").read_text(encoding="utf-8")
    assert "cursor)" in script_text


def test_source_links_the_article_and_keeps_one_quote() -> None:
    source_text = (
        _PLUGIN / "skills" / "deepstack-mode" / "references" / "source.md"
    ).read_text(encoding="utf-8")
    assert "Felix Rieseberg" in source_text
    assert "how-to-be-more-ambitious-a-tutorial-for-humans-with-models" in source_text
    assert source_text.count("I want a deeper version of this task") == 1
