import unittest

from tutor_framework.examples import (
    create_customer_service_example,
    create_creative_production_example,
    create_education_example,
    create_office_admin_example,
    list_reference_examples,
)
from tutor_framework.protocol.models import DecisionStatus


class ReferenceExampleTests(unittest.TestCase):
    def test_four_low_risk_examples_use_pack_contract(self):
        examples = list_reference_examples()
        self.assertEqual(
            {example.occupation_id for example in examples},
            {"office-admin", "customer-service", "education", "creative-production"},
        )
        for example in examples:
            with self.subTest(example=example.occupation_id):
                self.assertFalse(example.pack.external_writes)
                self.assertEqual(example.pack.execution_mode, "draft_only")

    def test_examples_return_drafts_without_external_actions(self):
        for factory in (
            create_office_admin_example,
            create_customer_service_example,
            create_education_example,
            create_creative_production_example,
        ):
            result = factory().run("Help me practise this task")
            self.assertEqual(result.status, DecisionStatus.DRAFT)
            self.assertIn("DRAFT", result.response)
            self.assertEqual(result.action_proposals, ())

    def test_empty_prompt_is_rejected(self):
        with self.assertRaises(ValueError):
            create_office_admin_example().run(" ")


if __name__ == "__main__":
    unittest.main()
