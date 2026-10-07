"""Exercise the deployed entrypoint, not only wording in SKILL.md."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/'scripts/learning_pack.py'


class InstalledLearningPack(unittest.TestCase):
    def invoke(self,*arguments,cwd=None):
        return subprocess.run([sys.executable,str(ENTRY),*map(str,arguments)],cwd=cwd,capture_output=True,text=True,timeout=60)

    def test_installed_entrypoint_is_executable_from_another_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            result=self.invoke('--help',cwd=temp)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('intake',result.stdout);self.assertIn('build',result.stdout)

    def test_doctor_reports_real_notes_route_without_fake_video_renderer(self):
        result=self.invoke('doctor')
        self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads(result.stdout)
        self.assertIn('notes',data['capabilities'])
        self.assertFalse(data['new_video_renderer'])

    def test_uploaded_text_produces_adaptive_questions_before_materials(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'handout.md'
            source.write_text('Explain why an analytical claim needs musical evidence.')
            result=self.invoke('intake',source,'--output',root/'intake','--language','zh-Hant',cwd=temp)
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads(result.stdout)
            self.assertEqual(data['intake']['state'],'awaiting_user')
            self.assertTrue(3<=len(data['intake']['questions'])<=5)
            self.assertFalse(list(root.rglob('lesson.mp4')))
            self.assertFalse(list(root.rglob('notes.pdf')))

    def test_installed_schema_and_version_match_learning_pack_contract(self):
        result=self.invoke('schema')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('PackContent',json.loads(result.stdout))
        self.assertIn('version: "3.4.0"',(ROOT/'SKILL.md').read_text())


if __name__=='__main__':unittest.main()
