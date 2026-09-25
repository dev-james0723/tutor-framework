"""Small, low-risk reference examples for pack authors."""

from dataclasses import dataclass

from tutor_framework.packs.manifest import OccupationPackManifest
from tutor_framework.protocol.models import DecisionStatus, TutorDecision


@dataclass(frozen=True)
class ReferenceExample:
    occupation_id: str
    display_name: str
    pack: OccupationPackManifest
    learning_mode: str

    def run(self, prompt: str) -> TutorDecision:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        return TutorDecision(
            decision_id=f"example-{self.occupation_id}",
            response=(
                f"[DRAFT] {self.display_name}: use this as a {self.learning_mode} "
                f"exercise for the request: {prompt.strip()}"
            ),
            confidence=0.6,
            status=DecisionStatus.DRAFT,
        )


def create_office_admin_example() -> ReferenceExample:
    return _example(
        "office-admin",
        "Office administration",
        "document-assistant",
        "document drafting",
    )


def create_customer_service_example() -> ReferenceExample:
    return _example(
        "customer-service",
        "Customer service",
        "customer-conversation-practice",
        "conversation practice",
    )


def create_education_example() -> ReferenceExample:
    return _example(
        "education",
        "Education",
        "sop-tutor",
        "lesson or procedure teaching",
    )


def create_creative_production_example() -> ReferenceExample:
    return _example(
        "creative-production",
        "Creative production",
        "source-backed-research",
        "source-backed creative research",
    )


def list_reference_examples() -> tuple[ReferenceExample, ...]:
    return (
        create_office_admin_example(),
        create_customer_service_example(),
        create_education_example(),
        create_creative_production_example(),
    )


def _example(
    occupation_id: str,
    display_name: str,
    pack_id: str,
    learning_mode: str,
) -> ReferenceExample:
    pack = OccupationPackManifest(
        pack_id=pack_id,
        version="0.1.0",
        family="common_workflow",
        display_name=display_name,
        occupations=(occupation_id,),
        capabilities=(pack_id,),
        supported_tasks=("draft", "practice"),
        safety_notes=("Keep the result as a draft or learning exercise.",),
        supported_locales=("en", "zh-Hant", "es"),
        external_writes=False,
        execution_mode="draft_only",
        status="common",
    )
    return ReferenceExample(occupation_id, display_name, pack, learning_mode)


__all__ = [
    "ReferenceExample",
    "create_customer_service_example",
    "create_creative_production_example",
    "create_education_example",
    "create_office_admin_example",
    "list_reference_examples",
]
