import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE='tutor_framework.domains.music.lesson.learning_pack'
REPO=Path(__file__).resolve().parents[2]


class LearningPackCLI(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,'-m',MODULE,*map(str,args)],
                              env={**os.environ,'PYTHONPATH':str(REPO/'src')},capture_output=True,text=True)

    def test_help_exposes_actual_intake_brief_build_verify_commands(self):
        result=self.run_cli('--help')
        self.assertEqual(result.returncode,0,result.stderr)
        for word in ('intake','brief','build','verify','doctor','schema'):
            self.assertIn(word,result.stdout)

    def test_doctor_does_not_claim_new_video_renderer(self):
        result=self.run_cli('doctor')
        self.assertEqual(result.returncode,0,result.stderr)
        info=json.loads(result.stdout)
        self.assertFalse(info['new_video_renderer'])
        self.assertIn('notes',info['capabilities'])

    def test_plain_intake_emits_questions_not_automatic_materials(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'handout.md';source.write_text('Explain the reasoning behind an analysis.')
            result=self.run_cli('intake',source,'--output',root/'intake','--language','zh-Hant')
            self.assertEqual(result.returncode,0,result.stderr)
            info=json.loads(result.stdout)
            self.assertEqual(info['intake']['state'],'awaiting_user')
            self.assertFalse(list(root.rglob('notes.pdf')))
            self.assertTrue(Path(info['dossier']).is_file())

    def test_schema_has_content_and_brief_models(self):
        result=self.run_cli('schema')
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads(result.stdout)
        self.assertIn('PackContent',value);self.assertIn('LearningBrief',value)

    def test_music_glyph_control_codes_are_not_readable_text(self):
        from tutor_framework.domains.music.lesson.learning_pack import document
        self.assertTrue(hasattr(document, 'has_readable_text'))
        self.assertFalse(document.has_readable_text('\x01' * 20))
        self.assertTrue(document.has_readable_text('Explain phrase function.'))

    def test_invalid_command_is_nonzero(self):
        result=self.run_cli('pretend-render')
        self.assertNotEqual(result.returncode,0)


if __name__=='__main__':unittest.main()
