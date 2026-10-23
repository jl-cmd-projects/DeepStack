"""Check Cloud distribution metadata against the packaged files."""

from __future__ import annotations

import json
import math
import posixpath
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import cast
from urllib.parse import unquote
from xml.etree import ElementTree
from zipfile import ZipFile, ZipInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SUPPORT_COPIES = (
    (
        "agents/deepstack-agent.md",
        "skills/deepstack-mode/references/deepstack-agent.md",
    ),
    ("models.json", "skills/deepstack-mode/references/models.json"),
)


def _metadata_text(manifest: dict[str, object], *all_names: str) -> str:
    cursor: object = manifest
    for each_name in all_names:
        if not isinstance(cursor, dict):
            raise TypeError("Invalid metadata object: " + ".".join(all_names))
        if each_name not in cursor:
            raise ValueError("Missing metadata: " + ".".join(all_names))
        cursor = cursor.get(each_name)
    if not isinstance(cursor, str) or not cursor.strip():
        raise ValueError("Missing metadata: " + ".".join(all_names))

    return cursor


def _manifest_path(all_names: list[str]) -> PurePosixPath:
    all_manifests = [
        PurePosixPath(each_name)
        for each_name in all_names
        if each_name.endswith(".codex-plugin/plugin.json")
    ]
    if len(all_manifests) != 1 or len(all_manifests[0].parts) not in (2, 3):
        raise ValueError("Package must contain one root Codex manifest")

    return all_manifests[0]


def _validate_archive_paths(all_names: list[str]) -> None:
    if len(all_names) != len(set(all_names)):
        raise ValueError("Duplicate archive member")
    for each_name in all_names:
        archive_path = PurePosixPath(each_name)
        if (
            "\\" in each_name
            or archive_path.is_absolute()
            or ".." in archive_path.parts
        ):
            raise ValueError("Unsafe archive path: " + each_name)


def _svg_dimensions(svg_bytes: bytes) -> tuple[float, float]:
    svg = ElementTree.fromstring(svg_bytes)
    if svg.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("Icon is not SVG")
    try:
        return float(svg.attrib["width"]), float(svg.attrib["height"])
    except (KeyError, ValueError):
        all_bounds = svg.attrib.get("viewBox", "").split()
        if len(all_bounds) != 4:
            raise ValueError("SVG needs numeric dimensions or a viewBox") from None

        return float(all_bounds[2]), float(all_bounds[3])


def _validate_svg_icon(package: ZipFile, plugin_root: PurePosixPath, icon: str) -> None:
    icon_path = PurePosixPath(icon)
    if (
        not icon.startswith("./")
        or ".." in icon_path.parts
        or icon_path.suffix != ".svg"
    ):
        raise ValueError("Icon must reference an included relative SVG")
    try:
        icon_bytes = package.read(str(plugin_root / icon_path))
    except KeyError:
        raise ValueError("Missing packaged icon: " + icon) from None
    width, height = _svg_dimensions(icon_bytes)
    if len(icon_bytes) > 5 * 1024 * 1024:
        raise ValueError("Icon exceeds 5 MiB")
    if not math.isfinite(width) or width != height or width < 48:
        raise ValueError("Icon must be square and at least 48 pixels")


def _validate_executable_hook(package: ZipFile, plugin_root: PurePosixPath) -> None:
    hook_path = str(plugin_root / "hooks/session-start.sh")
    hook = package.getinfo(hook_path)
    if not (hook.external_attr >> 16) & 0o111:
        raise ValueError("Packaged session hook must retain its executable mode")


def _relative_markdown_targets(markdown_bytes: bytes) -> frozenset[str]:
    all_targets = frozenset(
        unquote(each_match.group(1).split("#", 1)[0].strip())
        for each_match in MARKDOWN_LINK.finditer(markdown_bytes.decode("utf-8"))
    )

    return frozenset(
        each_target
        for each_target in all_targets
        if each_target
        and "://" not in each_target
        and not each_target.startswith("mailto:")
    )


def _validate_cloud_skill_links(package: ZipFile, plugin_root: PurePosixPath) -> None:
    skills_prefix = str(plugin_root / "skills") + "/"
    all_skill_files = frozenset(
        each_name
        for each_name in package.namelist()
        if each_name.startswith(skills_prefix)
    )
    for each_name in sorted(all_skill_files):
        if not each_name.endswith(".md"):
            continue
        for each_target in sorted(_relative_markdown_targets(package.read(each_name))):
            resolved_path = posixpath.normpath(
                str(PurePosixPath(each_name).parent / each_target)
            )
            if resolved_path not in all_skill_files:
                raise ValueError(
                    "Unshipped Cloud skill resource: "
                    + each_name
                    + " -> "
                    + each_target
                )


def _validate_support_copies(package: ZipFile, plugin_root: PurePosixPath) -> None:
    if str(plugin_root / "skills/deepstack-mode/SKILL.md") not in package.namelist():
        return
    for each_source, each_copy in SUPPORT_COPIES:
        try:
            canonical_bytes = package.read(str(plugin_root / each_source))
            skill_local_bytes = package.read(str(plugin_root / each_copy))
        except KeyError:
            raise ValueError("Missing skill-local support copy: " + each_copy) from None
        if canonical_bytes != skill_local_bytes:
            raise ValueError("Skill-local support copy differs: " + each_copy)


def validate_cloud_package(archive_path: Path) -> None:
    with ZipFile(archive_path) as package:
        _validate_archive_paths(package.namelist())
        manifest_path = _manifest_path(package.namelist())
        manifest = cast(dict[str, object], json.loads(package.read(str(manifest_path))))
        _metadata_text(manifest, "author", "name")
        for each_icon_field in ("composerIcon", "logo"):
            icon = _metadata_text(manifest, "interface", each_icon_field)
            _validate_svg_icon(package, manifest_path.parent.parent, icon)
        if "hooks" in manifest:
            _validate_executable_hook(package, manifest_path.parent.parent)
        _validate_cloud_skill_links(package, manifest_path.parent.parent)
        _validate_support_copies(package, manifest_path.parent.parent)


def _fixture_manifest() -> dict[str, object]:
    return {
        "author": {"name": "Package test"},
        "interface": {
            "composerIcon": "./assets/icon.svg",
            "logo": "./assets/icon.svg",
        },
    }


def _write_fixture(archive_path: Path, manifest: dict[str, object], svg: str) -> None:
    with ZipFile(archive_path, "w") as package:
        package.writestr(".codex-plugin/plugin.json", json.dumps(manifest))
        package.writestr("assets/icon.svg", svg)


def _tracked_file_modes() -> dict[str, int]:
    all_entries = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", "--stage", "-z"]
    ).split(b"\0")
    mode_by_path = {}
    for each_entry in all_entries:
        if each_entry:
            metadata, filename = each_entry.split(b"\t", 1)
            mode_by_path[filename.decode()] = int(metadata.split()[0], 8)

    return mode_by_path


def _write_source_archive(archive_path: Path) -> None:
    plugin_root = ROOT / "plugins/deepstack"
    mode_by_path = _tracked_file_modes()
    with ZipFile(archive_path, "w") as package:
        for each_path in sorted(plugin_root.rglob("*")):
            if each_path.is_file():
                member = ZipInfo(each_path.relative_to(plugin_root).as_posix())
                member.create_system = 3
                mode = mode_by_path.get(
                    each_path.relative_to(ROOT).as_posix(), 0o100644
                )
                member.external_attr = mode << 16
                package.writestr(member, each_path.read_bytes())


def test_source_package_meets_cloud_distribution_requirements(tmp_path: Path) -> None:
    archive_path = tmp_path / "deepstack.zip"
    _write_source_archive(archive_path)
    validate_cloud_package(archive_path)
    with ZipFile(archive_path) as package:
        all_skills = [
            each_name
            for each_name in package.namelist()
            if each_name.endswith("/SKILL.md")
        ]
        assert "skills/deepstack-mode/SKILL.md" in all_skills
        assert "skills/principle-outside-judge/SKILL.md" in all_skills


@pytest.mark.parametrize(
    "all_fields",
    [("author", "name"), ("interface", "composerIcon"), ("interface", "logo")],
)
def test_rejects_missing_distribution_metadata(
    tmp_path: Path, all_fields: tuple[str, str]
) -> None:
    manifest = _fixture_manifest()
    cast(dict[str, object], manifest[all_fields[0]]).pop(all_fields[1])
    archive_path = tmp_path / "missing-metadata.zip"
    _write_fixture(archive_path, manifest, '<svg width="64" height="64"/>')

    with pytest.raises(ValueError, match="Missing metadata: " + ".".join(all_fields)):
        validate_cloud_package(archive_path)


def test_rejects_missing_author_object(tmp_path: Path) -> None:
    manifest = _fixture_manifest()
    manifest.pop("author")
    archive_path = tmp_path / "missing-author.zip"
    _write_fixture(archive_path, manifest, '<svg width="64" height="64"/>')

    with pytest.raises(ValueError, match="Missing metadata: author.name"):
        validate_cloud_package(archive_path)


@pytest.mark.parametrize(
    "svg",
    [
        '<svg width="32" height="32"/>',
        '<svg width="64" height="48"/>',
        '<svg viewBox="0 0 64 48"/>',
    ],
)
def test_rejects_invalid_icon_dimensions(tmp_path: Path, svg: str) -> None:
    archive_path = tmp_path / "invalid-icon.zip"
    _write_fixture(archive_path, _fixture_manifest(), svg)

    with pytest.raises(ValueError, match="square and at least 48"):
        validate_cloud_package(archive_path)


def test_rejects_unshipped_icon(tmp_path: Path) -> None:
    manifest = _fixture_manifest()
    cast(dict[str, object], manifest["interface"])["logo"] = "./assets/missing.svg"
    archive_path = tmp_path / "missing-icon.zip"
    _write_fixture(archive_path, manifest, '<svg viewBox="0 0 64 64"/>')

    with pytest.raises(ValueError, match="Missing packaged icon"):
        validate_cloud_package(archive_path)


def test_rejects_nonexecutable_session_hook(tmp_path: Path) -> None:
    manifest = _fixture_manifest()
    manifest["hooks"] = "./hooks/codex-hooks.json"
    archive_path = tmp_path / "nonexecutable-hook.zip"
    _write_fixture(archive_path, manifest, '<svg viewBox="0 0 64 64"/>')
    with ZipFile(archive_path, "a") as package:
        package.writestr("hooks/session-start.sh", "exit 0\n")

    with pytest.raises(ValueError, match="executable mode"):
        validate_cloud_package(archive_path)


@pytest.mark.parametrize(
    "target", ["../../agents/deepstack-agent.md", "../../models.json"]
)
def test_rejects_skill_links_outside_cloud_resource_root(
    tmp_path: Path, target: str
) -> None:
    archive_path = tmp_path / "escaped-support.zip"
    _write_fixture(archive_path, _fixture_manifest(), '<svg viewBox="0 0 64 64"/>')
    with ZipFile(archive_path, "a") as package:
        package.writestr("skills/deepstack-mode/SKILL.md", "[support](" + target + ")")
        canonical_path = posixpath.normpath(
            str(PurePosixPath("skills/deepstack-mode") / target)
        )
        package.writestr(canonical_path, "support")

    with pytest.raises(ValueError, match="Unshipped Cloud skill resource"):
        validate_cloud_package(archive_path)


@pytest.mark.parametrize("target", ["../../../../models.json", "missing.md"])
def test_rejects_unshipped_transitive_skill_resource(
    tmp_path: Path, target: str
) -> None:
    archive_path = tmp_path / "transitive-support.zip"
    _write_fixture(archive_path, _fixture_manifest(), '<svg viewBox="0 0 64 64"/>')
    with ZipFile(archive_path, "a") as package:
        package.writestr("skills/deepstack-mode/SKILL.md", "[leaf](references/leaf.md)")
        package.writestr(
            "skills/deepstack-mode/references/leaf.md", "[support](" + target + ")"
        )
        package.writestr("models.json", "{}")

    with pytest.raises(ValueError, match="Unshipped Cloud skill resource"):
        validate_cloud_package(archive_path)


@pytest.mark.parametrize("canonical_path, copy_path", SUPPORT_COPIES)
def test_skill_local_support_matches_native_defaults(
    canonical_path: str, copy_path: str
) -> None:
    plugin_root = ROOT / "plugins/deepstack"

    assert (plugin_root / copy_path).read_bytes() == (
        plugin_root / canonical_path
    ).read_bytes()


@pytest.mark.parametrize("canonical_path, copy_path", SUPPORT_COPIES)
def test_rejects_divergent_skill_local_support_copy(
    tmp_path: Path, canonical_path: str, copy_path: str
) -> None:
    archive_path = tmp_path / "divergent-support.zip"
    _write_source_archive(archive_path)
    with ZipFile(archive_path) as package:
        canonical_bytes = package.read(canonical_path)
        all_members = [
            (each_member, package.read(each_member))
            for each_member in package.infolist()
        ]
    with ZipFile(archive_path, "w") as package:
        for each_member, each_bytes in all_members:
            packaged_bytes = (
                canonical_bytes + b"\n"
                if each_member.filename == copy_path
                else each_bytes
            )
            package.writestr(each_member, packaged_bytes)

    with pytest.raises(ValueError, match="Skill-local support copy differs"):
        validate_cloud_package(archive_path)


def test_source_archive_retains_all_tracked_hook_modes(tmp_path: Path) -> None:
    archive_path = tmp_path / "hook-modes.zip"
    _write_source_archive(archive_path)
    mode_by_path = _tracked_file_modes()
    with ZipFile(archive_path) as package:
        for each_path, each_mode in mode_by_path.items():
            if each_path.startswith("plugins/deepstack/hooks/"):
                packaged_hook = package.getinfo(
                    each_path.removeprefix("plugins/deepstack/")
                )
                assert packaged_hook.external_attr >> 16 == each_mode


def test_source_archive_is_repeatable(tmp_path: Path) -> None:
    first_archive = tmp_path / "first.zip"
    second_archive = tmp_path / "second.zip"
    _write_source_archive(first_archive)
    _write_source_archive(second_archive)

    assert first_archive.read_bytes() == second_archive.read_bytes()


if __name__ == "__main__":
    validate_cloud_package(Path(sys.argv[1]))
