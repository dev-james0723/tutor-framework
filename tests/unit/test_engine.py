import unittest

from tutor_framework.core.engine import (
    CapabilityRegistry,
    DomainReader,
    LearnerState,
    TeachingProfile,
    TutorEngine,
    TutorSession,
)
from tutor_framework.protocol.models import (
    ArtifactReadResult,
    LocalizationContext,
    TaskIntent,
    ToolManifest,
    TutorDecision,
)


class RecordingReader(DomainReader):
    def __init__(self, result):
        self.result = result
        self.seen = []

    def read(self, intent):
        self.seen.append(intent)
        return self.result


class RecordingCapabilities(CapabilityRegistry):
    def __init__(self, manifests):
        self.manifests = tuple(manifests)
        self.calls = 0

    def available(self, intent):
        self.calls += 1
        return self.manifests


class RecordingProfile(TeachingProfile):
    profile_id = "generic-profile"

    def __init__(self, decision):
        self.decision = decision
        self.calls = []

    def decide(self, intent, learner_state, artifact, capabilities):
        self.calls.append((intent, learner_state, artifact, capabilities))
        return self.decision


class TutorEngineTests(unittest.TestCase):
    def test_run_turn_coordinates_interfaces_and_records_session(self):
        intent = TaskIntent("Explain this document", task_type="explain")
        learner = LearnerState(
            learner_id="learner-1",
            locale=LocalizationContext(language="zh-Hant", locale="zh-HK"),
            goals=("communicate clearly",),
        )
        session = TutorSession("session-1", learner)
        artifact = ArtifactReadResult("doc-1", "text/plain", "A document")
        decision = TutorDecision("decision-1", "Here is the explanation.", 0.9)
        reader = RecordingReader(artifact)
        capabilities = RecordingCapabilities(
            (ToolManifest("local-files", "1.0", "Read local files"),)
        )
        profile = RecordingProfile(decision)
        engine = TutorEngine(reader, profile, capabilities)

        result = engine.run_turn(intent, session)

        self.assertIs(result, decision)
        self.assertEqual(reader.seen, [intent])
        self.assertEqual(capabilities.calls, 1)
        self.assertEqual(len(profile.calls), 1)
        self.assertIs(profile.calls[0][1], learner)
        self.assertIs(profile.calls[0][2], artifact)
        self.assertEqual(len(session.turns), 1)
        self.assertIs(session.turns[0].decision, decision)

    def test_engine_rejects_invalid_interface_outputs(self):
        intent = TaskIntent("Do a task")
        session = TutorSession("s", LearnerState("l"))
        reader = RecordingReader(object())
        profile = RecordingProfile(TutorDecision("d", "ok", 1.0))
        engine = TutorEngine(reader, profile, RecordingCapabilities(()))
        with self.assertRaises(TypeError):
            engine.run_turn(intent, session)

    def test_session_keeps_turns_isolated_and_validates_decisions(self):
        session = TutorSession("s", LearnerState("l1"))
        session.record_turn(TaskIntent("x"), TutorDecision("d", "x", 0.5), None)
        self.assertEqual(len(session.turns), 1)
        with self.assertRaises(TypeError):
            session.record_turn(TaskIntent("y"), object(), None)


if __name__ == "__main__":
    unittest.main()
