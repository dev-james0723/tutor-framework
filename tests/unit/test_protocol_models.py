import json
import unittest

from tutor_framework.protocol.models import (
    ActionProposal,
    Anchor,
    ArtifactReadResult,
    Claim,
    ClaimStatus,
    ConsentRecord,
    DecisionStatus,
    EvidenceRef,
    LocalizationContext,
    OccupationProfile,
    ProposalStatus,
    RiskClass,
    SkillManifest,
    SourceKind,
    TaskIntent,
    ToolManifest,
    TutorDecision,
    deserialize_model,
)


class ProtocolModelTests(unittest.TestCase):
    def test_nested_models_round_trip_with_stable_field_order(self):
        anchor = Anchor(
            artifact_id="lesson-1",
            locator="page:2#line:4",
            excerpt="Check the denominator.",
        )
        evidence = EvidenceRef(
            ref_id="e-1",
            source_uri="local://lesson-1",
            source_kind=SourceKind.LOCAL_FILE,
            anchors=(anchor,),
        )
        claim = Claim(
            claim_id="c-1",
            statement="The fraction has a common denominator.",
            confidence=0.92,
            status=ClaimStatus.SUPPORTED,
            evidence=(evidence,),
        )
        decision = TutorDecision(
            decision_id="d-1",
            response="Let us compare the denominators first.",
            confidence=0.9,
            claims=(claim,),
            status=DecisionStatus.READY,
        )

        encoded = decision.to_json()
        self.assertEqual(
            encoded.index('"schema_version"'),
            1,
        )
        self.assertEqual(encoded, decision.to_json())
        restored = deserialize_model(encoded, TutorDecision)
        self.assertEqual(restored, decision)
        self.assertEqual(json.loads(encoded)["claims"][0]["status"], "supported")

    def test_all_public_models_round_trip(self):
        models = (
            Anchor("a", "line:1"),
            EvidenceRef("e", "memory://e"),
            Claim("c", "A statement", 0.5),
            ArtifactReadResult("a", "text/plain", "content"),
            TutorDecision("d", "response", 0.5),
            TaskIntent("draft a reply"),
            OccupationProfile("office-admin", "Office administrator", "office"),
            ToolManifest("local-files", "1.0", "Read local files"),
            SkillManifest("document-assistant", "1.0", "Work with documents"),
            ConsentRecord("consent-1", ("local-file-read",), granted=True),
            LocalizationContext(),
            ActionProposal("action-1", "save-draft", "Save a draft"),
        )
        for model in models:
            with self.subTest(model=type(model).__name__):
                self.assertEqual(
                    deserialize_model(model.to_json(), type(model)),
                    model,
                )

    def test_confidence_and_enum_values_are_checked(self):
        with self.assertRaises(ValueError):
            Claim("c", "bad", 1.1)
        with self.assertRaises(ValueError):
            Claim("c", "bad", -0.1)
        with self.assertRaises(TypeError):
            Claim("c", "bad", True)
        with self.assertRaises(TypeError):
            ActionProposal("a", "write", "bad", risk_class="not-an-enum")
        with self.assertRaises(ValueError):
            RiskClass("not-a-risk")

    def test_non_json_safe_values_and_unknown_fields_are_rejected(self):
        with self.assertRaises(TypeError):
            TaskIntent("bad", context={"object": object()})

        payload = json.loads(TaskIntent("draft").to_json())
        payload["unexpected"] = "not allowed"
        with self.assertRaises(ValueError):
            deserialize_model(json.dumps(payload), TaskIntent)

    def test_action_proposals_default_to_unexecuted_and_explicit_risk(self):
        proposal = ActionProposal("a", "send-email", "Send an email")
        self.assertEqual(proposal.status, ProposalStatus.PROPOSED)
        self.assertTrue(proposal.requires_confirmation)
        self.assertFalse(proposal.external_write)


if __name__ == "__main__":
    unittest.main()
