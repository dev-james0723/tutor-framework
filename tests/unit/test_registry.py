import unittest

from tutor_framework.core.registry import (
    AudioConnector,
    DocumentConnector,
    ImageConnector,
    InMemoryCapabilityRegistry,
    LocalFileConnector,
    MapConnector,
    OccupationRegistry,
    SchedulingConnector,
    SpreadsheetConnector,
    WebSourceConnector,
)
from tutor_framework.protocol.models import (
    CapabilityAvailability,
    LocalizationContext,
    OccupationProfile,
    TaskIntent,
    ToolManifest,
)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.office = OccupationProfile(
            "office-admin",
            "Office administrator",
            "office_admin",
            supported_tasks=("draft", "organize"),
            capabilities=("documents", "spreadsheets"),
        )
        self.customer = OccupationProfile(
            "customer-service",
            "Customer service",
            "customer_service",
            supported_tasks=("practice",),
        )
        self.registry = OccupationRegistry((self.office, self.customer))

    def test_routes_hint_and_preserves_localization_context(self):
        context = LocalizationContext(language="zh-Hant", locale="zh-HK", units="metric")
        route = self.registry.route(
            TaskIntent("draft a response", task_type="draft", occupation_hint="office-admin"),
            localization=context,
        )
        self.assertIs(route.profile, self.office)
        self.assertEqual(route.localization, context)
        self.assertFalse(route.used_correction)

    def test_explicit_user_correction_overrides_hint(self):
        route = self.registry.route(
            TaskIntent("practice", task_type="practice", occupation_hint="office-admin"),
            user_correction="customer-service",
        )
        self.assertIs(route.profile, self.customer)
        self.assertTrue(route.used_correction)

    def test_unknown_correction_is_not_silently_routed(self):
        route = self.registry.route(TaskIntent("do work"), user_correction="unknown")
        self.assertIsNone(route.profile)
        self.assertTrue(route.requires_user_input)

    def test_capability_registry_returns_unavailable_result(self):
        available = ToolManifest(
            "local-files", "1.0", "Read local files",
            availability=CapabilityAvailability.AVAILABLE,
        )
        capabilities = InMemoryCapabilityRegistry((available,))
        self.assertTrue(capabilities.resolve("local-files").available)
        missing = capabilities.resolve("audio-input")
        self.assertFalse(missing.available)
        self.assertEqual(missing.capability_id, "audio-input")
        self.assertEqual(capabilities.available(TaskIntent("read")), (available,))

    def test_connector_interfaces_cover_common_artifact_surfaces(self):
        expected = (
            (LocalFileConnector, "read"),
            (ImageConnector, "read"),
            (AudioConnector, "transcribe"),
            (DocumentConnector, "read"),
            (SpreadsheetConnector, "read"),
            (WebSourceConnector, "search"),
            (MapConnector, "lookup"),
            (SchedulingConnector, "propose_event"),
        )
        for interface, method in expected:
            with self.subTest(interface=interface.__name__):
                self.assertTrue(hasattr(interface, method))


if __name__ == "__main__":
    unittest.main()
