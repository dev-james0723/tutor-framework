import json
import unittest
from tutor_framework.protocol.models import Claim, ClaimStatus
from tutor_framework.domains.music.global_theory.evidence import EvidenceSnapshot, EvidenceLedger


class ExistingProvenanceBridge(unittest.TestCase):
    def test_existing_claim_contract_retains_global_revision_and_kind(self):
        evidence = EvidenceSnapshot('claim-original',1,'pedagogical_example','Original duration example',
                                    'example-source','v1','system_exercise')
        claim = evidence.to_framework_claim(source_uri='urn:synthetic:example-source', confidence=0.8)
        self.assertIsInstance(claim, Claim)
        self.assertEqual(claim.claim_id, evidence.claim_id)
        self.assertEqual(claim.status, ClaimStatus.INFERRED)
        self.assertEqual(json.loads(claim.notes)['source_version'],'v1')
        self.assertEqual(json.loads(claim.notes)['kind'],'pedagogical_example')

    def test_licensed_content_cannot_become_unscoped_public_evidence(self):
        with self.assertRaises(ValueError):
            EvidenceSnapshot('licensed',1,'source_statement','Local licensed content','source','v1','licensed_content')
        record = EvidenceSnapshot('licensed',1,'source_statement','Local licensed content','source','v1','licensed_content','learner-a')
        with self.assertRaises(ValueError):
            EvidenceLedger(tenant_id='learner-b').append(record)

    def test_boolean_revision_is_not_a_version_number(self):
        with self.assertRaises(ValueError):
            EvidenceSnapshot('c',True,'uncertain','Needs review','s','v1','public_catalogue')


if __name__ == '__main__':
    unittest.main()
