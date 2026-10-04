"""HTTP transport contracts; the existing Python domain owns musical semantics."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

class OperationRequest(StrictRequest):
    inputs: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)

class ScoreRequest(StrictRequest):
    filename: str = Field(min_length=1, max_length=200)
    data_base64: str = Field(max_length=2800000)
    source_id: str = Field(min_length=1, max_length=200)
    context: dict[str, Any] = Field(default_factory=dict)

class PracticeRequest(StrictRequest):
    grade: int = Field(default=1, ge=1, le=5)
    seed: int = Field(ge=0, le=2147483647)
    item_index: int = Field(default=0, ge=0, le=4)
    topic: str = Field(default="fundamentals", max_length=80)
    mode: Literal["practice", "check"] = "practice"
    action: Literal["submit", "hint"] = "submit"
    response: str | None = Field(default=None, max_length=20000)

class CurriculumRequest(StrictRequest):
    source_id: str = Field(min_length=1,max_length=200)
    target_id: str = Field(min_length=1,max_length=200)
    source_version: str | None = Field(default=None,max_length=200)
    target_version: str | None = Field(default=None,max_length=200)

class ReconcileRequest(StrictRequest):
    records: list[dict[str,Any]] = Field(max_length=100)

class Envelope(BaseModel):
    request_id: str
    engine_version: str
    status: str
    payload: dict[str, Any]
    warnings: list[Any] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    review_required: bool
