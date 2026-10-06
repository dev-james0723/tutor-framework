"""Universal score-ingest routing for Theory Pedagogy.

The framework can parse explicit MusicXML directly. Printed scores and formats
that need conversion stay behind an adapter boundary; lack of an adapter is a
review state, never permission to guess notation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, runtime_checkable

from tutor_framework.domains.music.global_theory.context import LearnerContext
from tutor_framework.domains.music.global_theory.score_workflow import analyze_score


DIRECT_SYMBOLIC_EXTENSIONS = {".musicxml", ".xml"}
ADAPTER_EXTENSIONS = {
    ".mxl", ".mscz", ".mscx", ".pdf", ".png", ".jpg", ".jpeg",
    ".tif", ".tiff", ".bmp",
}


@dataclass(frozen=True)
class ScoreReadResult:
    state: str
    source_id: str
    input_kind: str
    observations: Mapping[str, object] | None = None
    adapter_result: Mapping[str, object] | None = None
    review_required: bool = False
    reason: str = ""

    @property
    def symbolic_available(self) -> bool:
        return bool(
            self.observations
            and self.observations.get("state") == "symbolic_observations_available"
        )


@runtime_checkable
class ScoreIngestAdapter(Protocol):
    def read(
        self,
        source: Path,
        *,
        source_id: str,
        output_dir: Path | None = None,
    ) -> Mapping[str, object]: ...


def read_score_source(
    source: Path | str,
    *,
    source_id: str,
    context: LearnerContext | None = None,
    adapter: ScoreIngestAdapter | None = None,
    output_dir: Path | None = None,
) -> ScoreReadResult:
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("source_id must be non-empty")
    source = Path(source).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"score source does not exist: {source}")
    suffix = source.suffix.casefold()

    if suffix in DIRECT_SYMBOLIC_EXTENSIONS:
        observations = analyze_score(
            source.read_bytes(),
            source_id=source_id,
            context=context or LearnerContext(),
        )
        return ScoreReadResult(
            state=str(observations["state"]),
            source_id=source_id,
            input_kind="symbolic",
            observations=observations,
            review_required=observations["state"] != "symbolic_observations_available",
        )

    if suffix not in ADAPTER_EXTENSIONS:
        return ScoreReadResult(
            state="unsupported",
            source_id=source_id,
            input_kind="unsupported",
            review_required=True,
            reason=f"unsupported score format: {suffix or '[none]'}",
        )

    input_kind = "printed_omr" if suffix in {
        ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"
    } else "symbolic_conversion"

    if adapter is None:
        return ScoreReadResult(
            state="review_required",
            source_id=source_id,
            input_kind=input_kind,
            review_required=True,
            reason="score conversion/OMR adapter is not configured",
        )

    try:
        result = adapter.read(source, source_id=source_id, output_dir=output_dir)
    except Exception as exc:
        return ScoreReadResult(
            state="validation_unavailable",
            source_id=source_id,
            input_kind=input_kind,
            review_required=True,
            reason=f"score adapter unavailable: {type(exc).__name__}",
        )
    if not isinstance(result, Mapping):
        return ScoreReadResult(
            state="validation_unavailable",
            source_id=source_id,
            input_kind=input_kind,
            review_required=True,
            reason="score adapter returned an invalid result",
        )

    state = str(result.get("state") or result.get("status") or "review_required")
    review_required = state not in {
        "symbolic_observations_available",
        "passed",
        "ready",
        "completed",
    }
    if input_kind == "printed_omr" and result.get("omr_verified") is not True:
        review_required = True
    if result.get("validation") in {"review_required", "validation_unavailable", "failed"}:
        review_required = True

    return ScoreReadResult(
        state=state,
        source_id=source_id,
        input_kind=input_kind,
        adapter_result=dict(result),
        review_required=review_required,
        reason=str(result.get("reason") or ""),
    )