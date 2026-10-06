"""Reusable music-artifact capabilities for the Theory Pedagogy Assistant."""

from .examples import (
    TheoryContrastSet,
    TheoryExampleVariant,
    available_concepts,
    build_piano_musicxml,
    generate_theory_contrast,
    write_contrast_package,
)
from .lecture_mapper import (
    TranscriptSegment,
    map_caplin_manifest,
    map_lecture_analysis,
)
from .score_reader import (
    ADAPTER_EXTENSIONS,
    DIRECT_SYMBOLIC_EXTENSIONS,
    ScoreIngestAdapter,
    ScoreReadResult,
    read_score_source,
)

__all__ = [
    "ADAPTER_EXTENSIONS",
    "DIRECT_SYMBOLIC_EXTENSIONS",
    "ScoreIngestAdapter",
    "ScoreReadResult",
    "TheoryContrastSet",
    "TheoryExampleVariant",
    "TranscriptSegment",
    "available_concepts",
    "build_piano_musicxml",
    "generate_theory_contrast",
    "map_caplin_manifest",
    "map_lecture_analysis",
    "read_score_source",
    "write_contrast_package",
]