"""Executable safety contracts for the reusable lesson compiler."""
import importlib
import unittest
from datetime import datetime, timezone, timedelta

H = "a" * 64
J = "b" * 64


class LessonContracts(unittest.TestCase):
    def setUp(self):
        try:
            self.m = importlib.import_module("tutor_framework.domains.music.lesson.models")
            self.t = importlib.import_module("tutor_framework.domains.music.lesson.trust")
        except ImportError:
            self.fail("typed lesson models and trust gates have not been implemented")

    def review(self, status="passed", hashes=None):
        return self.m.ReviewRecord("notes", self.m.CheckState(status), hashes or {"score": H}, "visual note comparison", "reviewer", "bounded comparison")

    def test_pass_requires_current_input_hashes(self):
        self.assertEqual(self.t.effective_review(self.review(), {"score": H}), "passed")
        self.assertEqual(self.t.effective_review(self.review(), {"score": J}), "review_required")

    def test_missing_review_is_unavailable_not_passed(self):
        self.assertEqual(self.t.effective_review(None, {"score": H}), "validation_unavailable")

    def test_unavailable_does_not_become_passed(self):
        r = self.review("validation_unavailable")
        self.assertEqual(self.t.effective_review(r, {"score": H}), "validation_unavailable")

    def test_review_requires_exact_not_subset_binding(self):
        self.assertEqual(self.t.effective_review(self.review(), {"score": H, "audio": J}), "review_required")

    def test_pass_without_reviewer_or_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            self.m.ReviewRecord("notes", self.m.CheckState.PASSED, {}, "", "", "")

    def test_protocol_roundtrip_and_unknown_field_rejection(self):
        r = self.review()
        self.assertEqual(self.m.ReviewRecord.from_dict(r.to_dict()).to_dict(), r.to_dict())
        p = r.to_dict(); p["pretend_passed"] = True
        with self.assertRaises(ValueError):
            self.m.ReviewRecord.from_dict(p)

    def test_invalid_hash_rejected(self):
        with self.assertRaises(ValueError):
            self.review(hashes={"score": "fake-hash"})

    def test_repeat_occurrence_contract(self):
        visits = (self.m.MeasureVisit("24a", 1), self.m.MeasureVisit("17", 2), self.m.MeasureVisit("24b", 1))
        p = self.m.Passage("beethoven:119:1:B", "edition-1", visits, ("P1", "P2"), "R=N")
        self.assertEqual(p.visits[1].occurrence, 2)
        with self.assertRaises(ValueError):
            self.m.Passage("p", "e", (visits[0], visits[0]), ("P1",), "R=N")

    def test_boolean_occurrence_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            self.m.MeasureVisit("1", True)

    def test_empty_passage_and_missing_edition_rejected(self):
        with self.assertRaises(ValueError):
            self.m.Passage("p", "", (), (), "R=N")

    def test_context_requires_passage_relevance_and_source_locator(self):
        from tutor_framework.protocol.models import EvidenceRef, Anchor
        evidence = EvidenceRef("ref", "https://example.org/archive", anchors=(Anchor("archive", "catalogue section 2"),), content_hash=H)
        c = self.m.ContextCard("context", "passage", self.m.ClaimKind.HISTORICAL_FACT, "An evidenced historical statement.", "Hear the present passage without assuming one uniform compositional period.", (evidence,))
        self.assertEqual(c.kind, self.m.ClaimKind.HISTORICAL_FACT)
        with self.assertRaises(ValueError):
            self.m.ContextCard("c", "p", self.m.ClaimKind.HISTORICAL_FACT, "Biography filler", "", (evidence,))
        with self.assertRaises(ValueError):
            self.m.ContextCard("c", "p", self.m.ClaimKind.HISTORICAL_FACT, "Claim", "Relevance", (EvidenceRef("r", "https://example.org"),))

    def test_audio_candidate_never_becomes_score_fact(self):
        for method in ("gemini_semantic", "basic_pitch", "symbolic_chroma_subsequence_dtw"):
            self.assertFalse(self.t.can_promote_music_evidence(method=method, similarity=1.0, corroborated=False, score_review=None))

    def test_september_28_false_identification_fixture(self):
        # Incorrect Carmen/Vivaldi recognition and K504 low alignment are regressions, not answers.
        self.assertFalse(self.t.can_promote_music_evidence(method="gemini_semantic", similarity=0.99, corroborated=False, score_review=self.review()))
        self.assertFalse(self.t.can_promote_music_evidence(method="symbolic_chroma_subsequence_dtw", similarity=0.5803, corroborated=False, score_review=None))
        self.assertFalse(self.t.can_promote_music_evidence(method="basic_pitch", similarity=None, corroborated=False, score_review=None))

    def test_human_alignment_degrades_without_independent_anchors(self):
        self.assertEqual(self.t.highlight_level("human_performance", independent_errors_ms=(), phrase_verified=False), "static")
        self.assertEqual(self.t.highlight_level("human_performance", independent_errors_ms=(), phrase_verified=True), "phrase")
        self.assertEqual(self.t.highlight_level("human_performance", independent_errors_ms=(20, 40, 60, 250), phrase_verified=True), "phrase")
        self.assertEqual(self.t.highlight_level("human_performance", independent_errors_ms=(20, 40, 60, 100), phrase_verified=True), "note")

    def test_synthetic_highlight_requires_measured_one_frame_accuracy(self):
        self.assertEqual(self.t.highlight_level("symbolic", independent_errors_ms=(), phrase_verified=True), "phrase")
        self.assertEqual(self.t.highlight_level("symbolic", independent_errors_ms=(5, 8, 15, 20), phrase_verified=True, fps=24), "note")
        self.assertEqual(self.t.highlight_level("symbolic", independent_errors_ms=(5, 8, 15, 80), phrase_verified=True, fps=24), "phrase")

    def test_remote_action_default_denied(self):
        self.assertFalse(self.t.authorized(provider="remote-tts", asset_hashes=(H,), private=True, estimated_usd=0, grants=()))

    def test_remote_grant_is_exact_provider_assets_cost_and_expiry(self):
        now = datetime.now(timezone.utc)
        g = self.m.ProductionGrant("approval", "remote-tts", (H,), True, 0.50, (now + timedelta(hours=1)).isoformat())
        self.assertTrue(self.t.authorized(provider="remote-tts", asset_hashes=(H,), private=True, estimated_usd=0.25, grants=(g,), now=now))
        for changes in ({"provider":"other"},{"asset_hashes":(J,)},{"estimated_usd":0.60},{"now":now+timedelta(hours=2)}):
            kw = dict(provider="remote-tts", asset_hashes=(H,), private=True, estimated_usd=0.25, grants=(g,), now=now); kw.update(changes)
            self.assertFalse(self.t.authorized(**kw))

    def test_negative_or_nan_cost_rejected(self):
        for cost in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.t.authorized(provider="x", asset_hashes=(), private=False, estimated_usd=cost, grants=())

    def test_private_grant_is_not_implied_by_paid_grant(self):
        g = self.m.ProductionGrant("approval", "x", (H,), False, 1.0, "2099-01-01T00:00:00+00:00")
        self.assertFalse(self.t.authorized(provider="x", asset_hashes=(H,), private=True, estimated_usd=0, grants=(g,)))

    def test_release_requires_all_checks_and_no_unavailable(self):
        self.assertFalse(self.t.release_ready({"decode":"passed", "listening":"validation_unavailable"}))
        self.assertFalse(self.t.release_ready({}))
        self.assertTrue(self.t.release_ready({"decode":"passed", "listening":"passed"}))

    def test_private_preview_is_not_public_rights_clearance(self):
        r = self.m.RightsRecord("public_domain", "user_provided", "unknown", "Local private review requested; no redistribution clearance")
        self.assertFalse(self.t.rights_allow_public(r))


if __name__ == "__main__":
    unittest.main()
