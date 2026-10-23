"""Exercise refreshes against a changing Git repository, including unchanged versions."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


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

    def test_install_rerun_and_relative_references(self):
        first = self.sync()
        self.assertEqual(first, self.sync())
        skill = (self.destination / "deepstack-mode/SKILL.md").resolve()
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
        self.assertIn("Update propagation marker", (self.destination / "deepstack-mode/SKILL.md").read_text())
        self.assertFalse((self.destination / "principle-room-to-miss").is_symlink())

    def test_new_runtime_home_reconstructed_from_persistent_state(self):
        first = self.sync()
        shutil.rmtree(self.destination.parent)
        fresh = self.root / "session-two/skills"
        result = self.sync(fresh)
        self.assertEqual(first["revision"], result["revision"])
        self.assertTrue((fresh / "deepstack-mode/SKILL.md").is_file())
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
        receipt = json.loads((self.state / "installation.json").read_text())
        self.assertEqual(first["revision"], receipt["revision"])
        self.assertEqual(first["revision"], (self.state / "current").resolve().name)

    def test_fetch_failure_preserves_current_skills(self):
        first = self.sync()
        shutil.rmtree(self.repository)
        with self.assertRaises(subprocess.CalledProcessError):
            self.sync()
        self.assertTrue((self.destination / "deepstack-mode/SKILL.md").is_file())
        self.assertEqual(first["revision"], (self.state / "current").resolve().name)

    def test_different_remote_rejected(self):
        self.sync()
        with self.assertRaises(ValueError):
            MODULE.sync("https://example.invalid/other", self.state, [self.destination])

    def test_interrupted_cache_initialization_recovers(self):
        self.state.mkdir(parents=True)
        MODULE.git("init", "--bare", str(self.state / "repository.git"))
        result = self.sync()
        self.assertEqual(self.git("rev-parse", "HEAD"), result["revision"])
        self.assertTrue((self.destination / "deepstack-mode/SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
