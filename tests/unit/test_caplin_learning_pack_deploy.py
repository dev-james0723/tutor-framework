import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
SCRIPT=REPO/'tools/deploy_caplin_learning_pack.py'


class CaplinPackDeploy(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(),'deployment entrypoint is not implemented')
        spec=importlib.util.spec_from_file_location('caplin_pack_deploy_tests',SCRIPT)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.skill=self.root/'caplin-form-tutor';(self.skill/'references').mkdir(parents=True)
        (self.skill/'SKILL.md').write_text('---\nname: caplin-form-tutor\nmetadata:\n  version: "3.3.0"\n---\n\n## Final teaching-video step\nOld automatic video instructions.\n\n## Learn mode\nPRIVATE KNOWLEDGE ROUTING PRESERVED\n')
        (self.skill/'references/teaching-video-workflow.md').write_text('# Existing whiteboard workflow\nKeep original musical evidence rules.\n')
        (self.skill/'references/private-knowledge.md').write_text('PRIVATE CORPUS MUST NOT CHANGE')
        self.original=(self.skill/'SKILL.md').read_bytes()

    def deploy(self,**kw):
        return self.module.deploy_installation(REPO,self.skill,Path(sys.executable),None,self.root/'backups',**kw)

    def test_dry_run_does_not_modify_existing_skill(self):
        result=self.deploy(dry_run=True)
        self.assertEqual((self.skill/'SKILL.md').read_bytes(),self.original)
        self.assertEqual(result['state'],'dry_run')
        self.assertFalse((self.skill/'scripts/learning_pack.py').exists())

    def test_deploy_is_real_and_preserves_private_corpus(self):
        result=self.deploy()
        self.assertEqual(result['state'],'deployed')
        skill=(self.skill/'SKILL.md').read_text()
        self.assertIn('version: "3.4.0"',skill)
        self.assertIn('3–5 adaptive questions',skill)
        self.assertIn('PRIVATE KNOWLEDGE ROUTING PRESERVED',skill)
        self.assertEqual((self.skill/'references/private-knowledge.md').read_text(),'PRIVATE CORPUS MUST NOT CHANGE')
        self.assertTrue((self.skill/'scripts/learning_pack.py').is_file())
        self.assertEqual(len(result['verification']['mismatched']),0)

    def test_entrypoint_runs_outside_repository_cwd(self):
        self.deploy()
        result=subprocess.run([sys.executable,str(self.skill/'scripts/learning_pack.py'),'doctor'],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('learning_brief',json.loads(result.stdout)['capabilities'])

    def test_redeployment_does_not_duplicate_sections(self):
        self.deploy();self.deploy()
        self.assertEqual((self.skill/'SKILL.md').read_text().count('## Learning Pack and goal setup'),1)
        self.assertEqual((self.skill/'references/teaching-video-workflow.md').read_text().count('Learning Pack selection gate'),1)

    def test_deploy_preserves_virtualenv_interpreter_symlink(self):
        bindir=self.root/'runtime/bin';bindir.mkdir(parents=True)
        interpreter=bindir/'python';interpreter.symlink_to(Path(sys.executable))
        self.module.deploy_installation(REPO,self.skill,interpreter,None,self.root/'backups')
        config=json.loads((self.skill/'learning-pack-runtime.json').read_text())
        self.assertEqual(config['python'],str(interpreter.absolute()))

    def test_no_second_skill_is_created(self):
        missing=self.root/'not-installed'
        with self.assertRaises(ValueError):self.module.deploy_installation(REPO,missing,Path(sys.executable),None,self.root/'backups')
        self.assertFalse(missing.exists())

    def test_backup_can_restore_prior_installed_state(self):
        result=self.deploy()
        self.module.rollback_installation(Path(result['backup']))
        self.assertEqual((self.skill/'SKILL.md').read_bytes(),self.original)
        self.assertFalse((self.skill/'scripts/learning_pack.py').exists())
        self.assertEqual((self.skill/'references/private-knowledge.md').read_text(),'PRIVATE CORPUS MUST NOT CHANGE')

    def test_deploy_copies_only_reviewed_license_identified_snapshots(self):
        self.deploy()
        folder=self.skill/'references/learning-pack-skills'
        data=json.loads((folder/'sources.lock.json').read_text())
        self.assertEqual(len(data['entries']),7)
        self.assertEqual(sum(x['upstream_snapshot_included'] for x in data['entries']),5)
        self.assertFalse(list(folder.rglob('*.sh')))


if __name__=='__main__':unittest.main()
