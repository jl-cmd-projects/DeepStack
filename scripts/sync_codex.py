"""Refresh DeepStack from Git and expose its skills without changing Codex config."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


REPOSITORY = "https://github.com/jl-cmd-projects/DeepStack.git"


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], text=True, stderr=subprocess.PIPE, timeout=120
    ).strip()


def sync(repository: str, state: Path, destinations: list[Path]) -> dict:
    state = state.expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True)
    with (state / "sync.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cache = state / "repository.git"
        if not cache.exists():
            with tempfile.TemporaryDirectory(dir=state) as temporary:
                staging_cache = Path(temporary) / "repository.git"
                git("init", "--bare", str(staging_cache))
                git("-C", str(staging_cache), "remote", "add", "origin", repository)
                staging_cache.rename(cache)
        if "origin" not in git("-C", str(cache), "remote").splitlines():
            git("-C", str(cache), "remote", "add", "origin", repository)
        if git("-C", str(cache), "remote", "get-url", "origin") != repository:
            raise ValueError("State directory belongs to another repository")
        git("-C", str(cache), "fetch", "--depth=1", "origin", "HEAD")
        revision = git("-C", str(cache), "rev-parse", "FETCH_HEAD")
        generation = state / "revisions" / revision
        if not generation.exists():
            generation.parent.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(dir=generation.parent) as temporary:
                staging = Path(temporary)
                git("--work-tree=" + str(staging), "--git-dir=" + str(cache),
                    "checkout", revision, "--", "plugins/deepstack")
                plugin = staging / "plugins/deepstack"
                skill_names(plugin)
                plugin.rename(generation)
        names = skill_names(generation)
        destinations = list(dict.fromkeys(path.expanduser().resolve() for path in destinations))
        for destination in destinations:
            entry = destination / "deepstack"
            if entry.is_symlink():
                if Path(os.readlink(entry)).parent != state / "revisions":
                    raise FileExistsError(f"Unmanaged installation already exists: {entry}")
            elif entry.exists():
                raise FileExistsError(f"Unmanaged installation already exists: {entry}")
            for name in names:
                flat_entry = destination / name
                if (flat_entry.exists() or flat_entry.is_symlink()) and not legacy_link(flat_entry, state):
                    raise FileExistsError(f"Unmanaged skill already exists: {flat_entry}")
        receipt = {"repository": repository, "revision": revision,
                   "skills": names, "links": [str(path / "deepstack") for path in destinations],
                   "cloud_catalog_verified": False, "fresh_cloud_session_verified": False}
        for destination in destinations:
            destination.mkdir(parents=True, exist_ok=True)
            entry = destination / "deepstack"
            with tempfile.TemporaryDirectory(prefix=".deepstack-", dir=destination) as temporary:
                pending = Path(temporary) / "entry"
                pending.symlink_to(generation, target_is_directory=True)
                pending.replace(entry)
            for old in destination.iterdir():
                if legacy_link(old, state):
                    old.unlink()
            manifests = state / "installations"
            manifests.mkdir(exist_ok=True)
            key = hashlib.sha256(os.fsencode(str(destination))).hexdigest()
            manifest = manifests / (key + ".json")
            pending_receipt = manifest.with_suffix(".next")
            pending_receipt.write_text(json.dumps({**receipt, "links": [str(entry)]}, indent=2) + "\n")
            pending_receipt.replace(manifest)
        return receipt


def skill_names(plugin: Path) -> list[str]:
    names = sorted(path.name for path in (plugin / "skills").iterdir() if (path / "SKILL.md").is_file())
    if "deepstack-mode" not in names or "deepstack-help" not in names:
        raise ValueError("Fetched repository lacks the DeepStack entry skills")
    return names


def legacy_link(path: Path, state: Path) -> bool:
    return path.is_symlink() and os.readlink(path) == str(state / "current/skills" / path.name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".local/share/deepstack")
    parser.add_argument("--skills-dir", type=Path, action="append")
    args = parser.parse_args()
    destinations = args.skills_dir or [Path.home() / ".agents/skills",
                                     Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"]
    try:
        print(json.dumps(sync(args.repository, args.state_dir, destinations), indent=2))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f"DeepStack synchronization failed: {error}\n")


if __name__ == "__main__":
    main()
