"""Exercise refreshes against a changing Git repository, including unchanged versions."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sync_codex", ROOT / "scripts/sync_codex.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CodexSyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repository = self.root / "upstream"
        self.repository.mkdir()
        self.plugin = self.repository / "plugins/deepstack"
        shutil.copytree(ROOT / "plugins/deepstack", self.plugin)
        self.git("init")
        self.git("config", "user.name", "DeepStack test")
        self.git("config", "user.email", "test@example.invalid")
        self.commit()
        self.state = self.root / "persistent/state"
        self.destination = self.root / "session-one/skills"

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repository), *args],
                                       text=True, stderr=subprocess.PIPE).strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-m", "Fixture update")

    def sync(self, destination=None):
        return MODULE.sync(str(self.repository), self.state, [destination or self.destination])

    def installed(self, name="deepstack-mode", destination=None):
        return (destination or self.destination) / "deepstack/skills" / name / "SKILL.md"

    def receipt(self):
        return json.loads(next((self.state / "installations").glob("*.json")).read_text())

    def test_install_rerun_and_relative_references(self):
        first = self.sync()
        self.assertEqual(first, self.sync())
        skill = self.installed().resolve()
        self.assertTrue((skill.parent / "../../agents/deepstack-agent.md").is_file())
        self.assertTrue((skill.parent / "../principle-outside-judge/SKILL.md").is_file())
        self.assertFalse(first["cloud_catalog_verified"])

    def test_same_version_update_and_removed_skill_propagate(self):
        first = self.sync()
        manifest_before = (self.plugin / ".codex-plugin/plugin.json").read_bytes()
        skill = self.plugin / "skills/deepstack-mode/SKILL.md"
        skill.write_text(skill.read_text() + "\nUpdate propagation marker\n")
        shutil.rmtree(self.plugin / "skills/principle-room-to-miss")
        self.commit()
        second = self.sync()
        self.assertNotEqual(first["revision"], second["revision"])
        self.assertEqual(manifest_before, (self.plugin / ".codex-plugin/plugin.json").read_bytes())
        self.assertIn("Update propagation marker", self.installed().read_text())
        self.assertFalse(self.installed("principle-room-to-miss").exists())

    def test_new_runtime_home_reconstructed_from_persistent_state(self):
        first = self.sync()
        shutil.rmtree(self.destination.parent)
        fresh = self.root / "session-two/skills"
        result = self.sync(fresh)
        self.assertEqual(first["revision"], result["revision"])
        self.assertTrue(self.installed(destination=fresh).is_file())
        self.assertFalse(result["fresh_cloud_session_verified"])

    def test_conflict_preserves_existing_installation(self):
        first = self.sync()
        skill = self.plugin / "skills/new-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: new-skill\ndescription: Test\n---\n")
        self.commit()
        (self.destination / "new-skill").mkdir()
        with self.assertRaises(FileExistsError):
            self.sync()
        receipt = self.receipt()
        self.assertEqual(first["revision"], receipt["revision"])
        self.assertEqual(first["revision"], (self.destination / "deepstack").resolve().name)

    def test_fetch_failure_preserves_current_skills(self):
        first = self.sync()
        shutil.rmtree(self.repository)
        with self.assertRaises(subprocess.CalledProcessError):
            self.sync()
        self.assertTrue(self.installed().is_file())
        self.assertEqual(first["revision"], (self.destination / "deepstack").resolve().name)

    def test_different_remote_rejected(self):
        self.sync()
        with self.assertRaises(ValueError):
            MODULE.sync("https://example.invalid/other", self.state, [self.destination])

    def test_interrupted_cache_initialization_recovers(self):
        self.state.mkdir(parents=True)
        MODULE.git("init", "--bare", str(self.state / "repository.git"))
        result = self.sync()
        self.assertEqual(self.git("rev-parse", "HEAD"), result["revision"])
        self.assertTrue(self.installed().is_file())

    def test_second_runtime_keeps_first_runtime_links(self):
        first = self.sync()
        second_destination = self.root / "session-two/skills"
        skill = self.plugin / "skills/deepstack-mode/SKILL.md"
        skill.write_text(skill.read_text() + "\nRuntime two revision\n")
        self.commit()
        second = self.sync(second_destination)
        self.assertNotEqual(first["revision"], second["revision"])
        self.assertTrue(self.installed().is_file())
        self.assertNotIn("Runtime two revision", self.installed().read_text())
        self.assertIn("Runtime two revision", self.installed(destination=second_destination).read_text())
        receipts = [json.loads(path.read_text()) for path in (self.state / "installations").glob("*.json")]
        by_destination = {item["links"][0]: item["revision"] for item in receipts}
        self.assertEqual({str(self.destination / "deepstack"): first["revision"],
                          str(second_destination / "deepstack"): second["revision"]}, by_destination)

    def test_interruption_after_revision_switch_leaves_no_broken_links(self):
        self.sync()
        shutil.rmtree(self.plugin / "skills/principle-room-to-miss")
        self.commit()
        replace = Path.replace

        def interrupt_switch(path, target):
            result = replace(path, target)
            if Path(target) in (self.state / "current", self.destination / "deepstack"):
                raise SystemExit("Interrupted after revision switch")
            return result

        with mock.patch.object(Path, "replace", interrupt_switch):
            try:
                self.sync()
            except SystemExit:
                pass
        broken = [path for path in self.destination.rglob("*") if path.is_symlink() and not path.exists()]
        self.assertEqual([], broken)
        self.assertTrue(self.installed().is_file())
        self.sync()
        self.assertFalse(self.installed("principle-room-to-miss").exists())

    def test_legacy_migration_preserves_other_runtime_and_current_pointer(self):
        first = self.sync()
        entry = self.destination / "deepstack"
        generation = entry.resolve()
        entry.unlink()
        current = self.state / "current"
        current.symlink_to(generation, target_is_directory=True)
        second_destination = self.root / "session-two/skills"
        second_destination.mkdir(parents=True)
        for destination in (self.destination, second_destination):
            for name in first["skills"]:
                (destination / name).symlink_to(current / "skills" / name, target_is_directory=True)
        shutil.rmtree(self.plugin / "skills/principle-room-to-miss")
        self.commit()
        self.sync(second_destination)
        self.assertEqual(generation, current.resolve())
        self.assertTrue((self.destination / "principle-room-to-miss/SKILL.md").is_file())
        self.assertTrue(self.installed(destination=second_destination).is_file())
        self.assertFalse((second_destination / "principle-room-to-miss").is_symlink())
        self.sync()
        self.assertTrue(self.installed().is_file())
        self.assertFalse((self.destination / "principle-room-to-miss").is_symlink())

    def test_process_death_at_each_filesystem_publication_boundary(self):
        old_revision = self.git("rev-parse", "HEAD")
        shutil.rmtree(self.plugin / "skills/principle-room-to-miss")
        skill = self.plugin / "skills/new-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: new-skill\ndescription: Test\n---\n")
        self.commit()
        new_revision = self.git("rev-parse", "HEAD")
        child = '''
import importlib.util, json, os, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("sync_codex", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
counter = [0]
def instrument(original):
    def call(*args, **kwargs):
        result = original(*args, **kwargs)
        counter[0] += 1
        if counter[0] == int(sys.argv[5]):
            os._exit(73)
        return result
    return call
for method in ("mkdir", "rename", "replace", "symlink_to", "unlink", "write_text"):
    setattr(Path, method, instrument(getattr(Path, method)))
module.sync(sys.argv[2], Path(sys.argv[3]), [Path(sys.argv[4])])
print(json.dumps(counter[0]))
'''
        boundary_count = None
        boundary = 0
        while boundary_count is None or boundary <= boundary_count:
            with self.subTest(boundary=boundary):
                state = self.root / f"crash-{boundary}/state"
                destination = self.root / f"crash-{boundary}/skills"
                self.git("update-ref", "HEAD", old_revision)
                MODULE.sync(str(self.repository), state, [destination])
                self.git("update-ref", "HEAD", new_revision)
                result = subprocess.run(
                    [sys.executable, "-c", child, str(ROOT / "scripts/sync_codex.py"),
                     str(self.repository), str(state), str(destination), str(boundary)],
                    text=True, capture_output=True, timeout=60,
                )
                if boundary == 0:
                    self.assertEqual(0, result.returncode, result.stderr)
                    boundary_count = json.loads(result.stdout)
                else:
                    self.assertEqual(73, result.returncode, result.stderr)
                self.assertTrue(self.installed(destination=destination).is_file())
                plugin = (destination / "deepstack").resolve()
                self.assertIn(plugin.name, (old_revision, new_revision))
                self.assertTrue((plugin / "agents/deepstack-agent.md").is_file())
                for link in destination.rglob("*"):
                    if link.is_symlink():
                        self.assertTrue(link.exists(), str(link))
                try:
                    MODULE.sync(str(self.repository), state, [destination])
                except subprocess.CalledProcessError as error:
                    self.fail(error.stderr)
                self.assertTrue(self.installed("new-skill", destination).is_file())
                self.assertFalse(self.installed("principle-room-to-miss", destination).exists())
            boundary += 1


if __name__ == "__main__":
    unittest.main()
