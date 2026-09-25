import unittest

from tutor_framework.protocol.models import (
    ActionProposal,
    Anchor,
    Claim,
    ClaimStatus,
    ConsentRecord,
    EvidenceRef,
    ProposalStatus,
    RiskClass,
    SourceKind,
)
from tutor_framework.core.policies import (
    PolicyOutcome,
    action_execution_decision,
    assess_supportability,
    consent_covers,
    memory_promotion_allowed,
    requires_human_review,
    resolve_conflict,
)


def supported_claim(
    claim_id: str,
    statement: str,
    confidence: float = 0.9,
) -> Claim:
    evidence = EvidenceRef(
        ref_id=f"e-{claim_id}",
        source_uri="local://lesson",
        source_kind=SourceKind.LOCAL_FILE,
        anchors=(Anchor("lesson", "line:1"),),
    )
    return Claim(
        claim_id=claim_id,
        statement=statement,
        confidence=confidence,
        status=ClaimStatus.SUPPORTED,
        evidence=(evidence,),
    )


class PolicyTests(unittest.TestCase):
    def test_supportability_requires_evidence_and_sufficient_confidence(self):
        claim = supported_claim("c1", "The source supports this.")
        self.assertEqual(assess_supportability(claim).outcome, PolicyOutcome.ALLOW)

        unsupported = Claim("c2", "Maybe", 0.95)
        self.assertEqual(
            assess_supportability(unsupported).outcome,
            PolicyOutcome.REVIEW_REQUIRED,
        )
        self.assertTrue(requires_human_review(Claim("c3", "Unclear", 0.2)))

        missing_anchor = Claim(
            "c4",
            "Source exists but its location is unclear.",
            0.95,
            status=ClaimStatus.SUPPORTED,
            evidence=(EvidenceRef("e4", "local://lesson"),),
        )
        self.assertTrue(requires_human_review(missing_anchor))

    def test_inferred_claims_cannot_be_promoted_without_review(self):
        inferred = supported_claim("c1", "A hypothesis")
        inferred.status = ClaimStatus.INFERRED
        self.assertFalse(memory_promotion_allowed(inferred, reviewed=True))
        confirmed = supported_claim("c2", "A reviewed fact", 0.95)
        confirmed.status = ClaimStatus.CONFIRMED
        self.assertFalse(memory_promotion_allowed(confirmed, reviewed=False))
        self.assertTrue(memory_promotion_allowed(confirmed, reviewed=True))

    def test_conflict_resolution_is_conservative(self):
        left = supported_claim("left", "The meeting is Tuesday", 0.91)
        right = supported_claim("right", "The meeting is Wednesday", 0.9)
        result = resolve_conflict((left, right))
        self.assertIsNone(result.chosen)
        self.assertTrue(result.requires_review)

        result = resolve_conflict((left,))
        self.assertEqual(result.chosen, left)
        self.assertFalse(result.requires_review)

    def test_consent_scope_is_explicit(self):
        consent = ConsentRecord(
            "consent-1", ("read:local-file", "draft:document"), granted=True
        )
        self.assertTrue(consent_covers(consent, "read:local-file"))
        self.assertFalse(consent_covers(consent, "write:local-file"))
        self.assertFalse(consent_covers(None, "read:local-file"))

    def test_restricted_and_external_actions_remain_proposed(self):
        restricted = ActionProposal(
            "a1", "give-medical-advice", "Provide advice", RiskClass.REGULATED,
            status=ProposalStatus.APPROVED,
        )
        result = action_execution_decision(restricted, human_review=True)
        self.assertEqual(result.outcome, PolicyOutcome.REVIEW_REQUIRED)
        self.assertFalse(result.execution_allowed)

        external = ActionProposal(
            "a2", "send-email", "Send email", RiskClass.LOW,
            external_write=True, status=ProposalStatus.APPROVED,
        )
        self.assertFalse(
            action_execution_decision(external, human_review=True).execution_allowed
        )

    def test_low_risk_approved_draft_can_execute_only_after_review(self):
        proposal = ActionProposal(
            "a3", "format-draft", "Format a local draft",
            status=ProposalStatus.APPROVED,
        )
        self.assertFalse(action_execution_decision(proposal).execution_allowed)
        self.assertTrue(
            action_execution_decision(proposal, human_review=True).execution_allowed
        )


if __name__ == "__main__":
    unittest.main()
