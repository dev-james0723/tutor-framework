"""Release acceptance for the guarded existing provider and command interface."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tutor_framework.domains.music.global_theory.mineru_adapter import ExistingMinerUHelper, ExistingMinerUResult
from tutor_framework.domains.music.global_theory.__main__ import main
from tests.unit import test_global_theory_owner_mineru as mineru_fixtures
from tests.unit.test_global_theory_owner_exam import original_pdf


class GlobalRuntimeRelease(unittest.TestCase):
    def test_real_helper_has_no_default_paid_or_cloud_operation(self):
        helper = ExistingMinerUHelper('resource', Path('/not-read.pdf'), Path('/not-created'), '0'*64)
        with self.assertRaises(PermissionError):
            helper(original_pdf())

    def test_missing_credential_fails_before_reading_pdf_or_starting_helper(self):
        helper = ExistingMinerUHelper('resource', Path('/not-read.pdf'), Path('/not-created'), '0'*64, True, True)
        with patch.dict(os.environ, {}, clear=True), patch('subprocess.run') as runner:
            with self.assertRaisesRegex(RuntimeError, 'MINERU_CREDENTIAL_UNAVAILABLE'):
                helper(original_pdf())
            runner.assert_not_called()

    def test_no_save_blocks_external_helper_even_with_consent(self):
        helper = ExistingMinerUHelper('resource', Path('/not-read.pdf'), Path('/not-created'), '0'*64, True, True, True)
        with self.assertRaises(PermissionError):
            helper(original_pdf())

    def test_existing_result_uses_the_same_original_checksum(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sha = mineru_fixtures.MinerUStructureAcceptance().result_directory(root)
            adapter = ExistingMinerUResult('original-fixture', root, sha)
            result = adapter(original_pdf())
            self.assertEqual(result['questions'][0]['original_number'], '1')
            self.assertFalse(result['new_api_submission'])
            with self.assertRaises(ValueError):
                adapter(original_pdf('Changed original'))

    def test_command_no_save_prevents_mini_export(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'forbidden'
            code = main(['mini-exam','--grade','1','--syllabus-id','abrsm-theory-from-2020',
                         '--seed','4','--no-save','--output',str(target)])
            self.assertEqual(code, 2)
            self.assertFalse(target.exists())

    def test_command_context_no_save_prevents_single_practice_export(self):
        with tempfile.TemporaryDirectory() as temp:
            context = Path(temp) / 'context.json'; context.write_text(json.dumps({'no_save':True}))
            target = Path(temp) / 'forbidden'
            code = main(['practice','--grade','1','--syllabus-id','abrsm-theory-from-2020',
                         '--competency-id','rhythm.duration','--seed','4','--context',str(context),'--output',str(target)])
            self.assertEqual(code, 2)
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
