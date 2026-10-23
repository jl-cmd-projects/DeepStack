"""Refresh DeepStack from Git and expose its skills without changing Codex config."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
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
                shutil.move(str(staging / "plugins" / "deepstack"), generation)
        skills = generation / "skills"
        names = sorted(path.name for path in skills.iterdir() if (path / "SKILL.md").is_file())
        if "deepstack-mode" not in names or "deepstack-help" not in names:
            raise ValueError("Fetched repository lacks the DeepStack entry skills")
        manifest = state / "installation.json"
        previous = json.loads(manifest.read_text()) if manifest.exists() else {"links": []}
        destinations = list(dict.fromkeys(path.expanduser().absolute() for path in destinations))
        links = [path / name for path in destinations for name in names]
        current = state / "current"
        for link in links:
            expected = current / "skills" / link.name
            if link.is_symlink() and os.readlink(link) == str(expected):
                continue
            if link.exists() or link.is_symlink():
                raise FileExistsError(f"Unmanaged skill already exists: {link}")
        temporary_link = state / "current.next"
        temporary_link.unlink(missing_ok=True)
        temporary_link.symlink_to(generation, target_is_directory=True)
        temporary_link.replace(current)
        for link in links:
            link.parent.mkdir(parents=True, exist_ok=True)
            if not link.is_symlink():
                link.symlink_to(current / "skills" / link.name, target_is_directory=True)
        for old in map(Path, previous["links"]):
            if old not in links and old.is_symlink() and os.readlink(old) == str(current / "skills" / old.name):
                old.unlink()
        receipt = {"repository": repository, "revision": revision,
                   "skills": names, "links": list(map(str, links)),
                   "cloud_catalog_verified": False, "fresh_cloud_session_verified": False}
        pending = manifest.with_suffix(".next")
        pending.write_text(json.dumps(receipt, indent=2) + "\n")
        pending.replace(manifest)
        return receipt


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
