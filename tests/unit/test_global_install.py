import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class GlobalInstallTest(unittest.TestCase):
    def test_temp_install_runs_without_repository_on_import_path(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            subprocess.run([sys.executable, str(ROOT / "tools/global_music_theory_install.py"),
                            "install", "--repository", str(ROOT), "--destination", str(destination),
                            "--with-caplin"], check=True, capture_output=True, text=True)
            executable = destination / "global-music-theory-super-skill/bin/global-music-theory"
            run = subprocess.run([str(executable), "doctor"], cwd=temp,
                                 check=True, capture_output=True, text=True, env={"PYTHONDONTWRITEBYTECODE": "1"})
            self.assertEqual(json.loads(run.stdout)["identity"], "global-music-theory-super-skill")
            self.assertTrue((destination / "global-music-theory-super-skill/private/caplin-baseline/SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
