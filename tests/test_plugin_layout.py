"""The published plugin keeps the slots a host install expects."""

from __future__ import annotations

import hashlib
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
    assert json.loads(silenced.stdout) == {}

    copilot = subprocess.run([script, "copilot"], check=False, capture_output=True, text=True, env=env)
    assert copilot.returncode == 0
    copilot_payload = json.loads(copilot.stdout)
    assert 'quote"dir' in copilot_payload["additionalContext"]

    unknown = subprocess.run([script, "nope"], check=False, capture_output=True, text=True, env=env)
    assert unknown.returncode == 2
    assert unknown.stdout == ""


def test_off_switch_accepts_a_trailing_carriage_return(tmp_path: Path) -> None:
    script = _PLUGIN / "hooks" / "session-start.sh"
    home = tmp_path / "home"
    home.mkdir()
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "CLAUDE_PLUGIN_ROOT": str(_PLUGIN),
            "COPILOT_PLUGIN_ROOT": str(_PLUGIN),
        }
    )

    def write_sheet(folder: str, body: bytes) -> None:
        path = home / folder / "deepstack-models.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

    def run(runtime: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [script, runtime], check=False, capture_output=True, text=True, env=env
        )

    write_sheet(".cursor", b"# note\r\nsession hook: off\r\n")
    cursor_off = run("cursor")
    assert cursor_off.returncode == 0
    assert json.loads(cursor_off.stdout) == {}

    write_sheet(".claude", b"altitude: inherit-parent\nsession hook: off\r\n")
    claude_off = run("claude")
    assert claude_off.returncode == 0
    assert claude_off.stdout == ""

    write_sheet(".claude", b"Session hook: off\n")
    claude_on = run("claude")
    assert claude_on.returncode == 0
    assert claude_on.stdout.startswith("DeepStack:")

    write_sheet(".copilot", b"session hook: off\r\n")
    copilot_off = run("copilot")
    assert copilot_off.returncode == 0
    assert copilot_off.stdout == ""

    write_sheet(".cursor", b"session hook: off please\n")
    cursor_near = run("cursor")
    assert cursor_near.returncode == 0
    payload = json.loads(cursor_near.stdout)
    assert "additional_context" in payload
    assert payload["additional_context"].startswith("DeepStack:")


def test_windows_hook_passes_the_runtime_and_the_off_switch() -> None:
    codex_hooks = json.loads((_PLUGIN / "hooks" / "codex-hooks.json").read_text(encoding="utf-8"))
    command_windows = codex_hooks["hooks"]["SessionStart"][0]["hooks"][0]["commandWindows"]
    assert "session-start.ps1" in command_windows
    assert command_windows.endswith(" codex")
    script = (_PLUGIN / "hooks" / "session-start.ps1").read_text(encoding="utf-8")
    assert "session hook: off" in script
    assert '.TrimEnd("`r")' in script
    assert "Write-Output '{}'" in script
    assert "additional_context" in script
    assert "additionalContext" in script
    assert "unknown runtime" in script


# Fingerprints of passages from the cited article. The words stay out of this tree.
_ARTICLE_FINGERPRINTS = {
    "c5c8f4dba151c729998ed2420e1e21047e837b1a1ca838243d809a4cefda77b5",
    "ad45e1e16f9195494020300351d96582bf43f0d08a0d08e88d7703cbc0bd4b08",
    "a9a3b6455bae6fe3ad571afaa6c148ec570ee4416197478c9b2074cdd3a46545",
    "f058dc2439198da901ddcb0a9bc2624c6c3b5b167e6b76d625a79793a6104d07",
    "426d722f6e7d505b43a8c9647a4a00435600ce504943ac31e38033947f529556",
    "19c8ffff2cc84db19c2c8b02196a8e011ef516613d9f0a97111725a4bd66028e",
    "87e0a511e7307fdd9ec70d0809163140b83d7db0eec99ecf7178e25d7a40c904",
    "9eafc63ae66470811cf6f11987fe343557d1c4ad792c1d67fb4184d9cde8f6dc",
    "68fff469cee3ff27a526dd002a5cca42684e9e78a64f022ecda55aad2f84f0eb",
    "ecda215a16617c44e06d0909510640854a82674ce5aa8cb1a1d988470619eb3d",
    "26eec2d6a6597a76562129e66013f396b5c1eb83c24d5381782b6e662998d7f0",
    "1a00175165b21377ab0d0a40092d52a65e4b2fcbf37572a1fe2aedc2e6d9d27d",
    "51402f8d201cb795977a00761ae9b89c3802608a8b27a1a2ed67da86f2b11b22",
    "78538c911036893abfad60cc9ce92c5aedfafa738bdcd5b940ec5d555dc51af4",
    "d1bb4a2da0bd6bc7937542c93b7d1441e72c0d6c796714e2b3214a6d96df2d72",
}
_WORD = re.compile(r"[a-z0-9']+")


def _fingerprints(text: str, size: int) -> set[str]:
    tokens = _WORD.findall(text.lower())
    found: set[str] = set()
    for index in range(len(tokens) - size + 1):
        window = " ".join(tokens[index : index + size])
        found.add(hashlib.sha256(window.encode()).hexdigest())
    return found


def test_source_credits_the_article_and_states_the_four_questions() -> None:
    source_text = (
        _PLUGIN / "skills" / "deepstack-mode" / "references" / "source.md"
    ).read_text(encoding="utf-8")
    assert "Felix Rieseberg" in source_text
    assert "how-to-be-more-ambitious-a-tutorial-for-humans-with-models" in source_text
    assert "What a top person in that field would do that this task left out." in source_text
    assert "The raw source to start from, before anyone summarized it." in source_text
    assert "The methods and tools that person would use." in source_text
    assert "What, other than the agent or the user, shows the result is right." in source_text
    assert not source_text.lstrip().startswith(">")
    assert "\n> " not in source_text


def test_tree_does_not_carry_article_passages() -> None:
    found: set[str] = set()
    for path in _ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {".md", ".json", ".py", ".yml", ".sh", ".ps1"}:
            continue
        text = path.read_text(encoding="utf-8")
        found.update(_fingerprints(text, 5))
        found.update(_fingerprints(text, 6))
        found.update(_fingerprints(text, 8))
    assert not found & _ARTICLE_FINGERPRINTS
