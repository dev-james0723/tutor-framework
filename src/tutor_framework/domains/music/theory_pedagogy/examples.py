"""Theory-pedagogy example generation from exact symbolic notation.

Generated examples are original teaching models. They are never promoted to
course evidence or source-score facts, and every set stays review-gated until a
human checks the intended analytical distinction.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from tutor_framework.domains.music.lesson.symbolic import parse_score


@dataclass(frozen=True)
class TheoryExampleVariant:
    variant_id: str
    title: str
    teaching_point: str
    musicxml: str
    annotations: tuple[str, ...] = ()
    status: str = "pedagogical_model_requires_analytical_review"

    def __post_init__(self) -> None:
        for name in ("variant_id", "title", "teaching_point"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
        if not isinstance(self.musicxml, str) or not self.musicxml.strip():
            raise ValueError("musicxml must be non-empty text")
        parse_score(self.musicxml)
        object.__setattr__(self, "annotations", tuple(self.annotations))


@dataclass(frozen=True)
class TheoryContrastSet:
    concept: str
    objective: str
    prompt: str
    variants: tuple[TheoryExampleVariant, ...]
    status: str = "pedagogical_model_requires_analytical_review"

    def __post_init__(self) -> None:
        for name in ("concept", "objective", "prompt"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
        object.__setattr__(self, "variants", tuple(self.variants))
        if len(self.variants) < 2:
            raise ValueError("a contrast set requires at least two variants")
        if len({item.variant_id for item in self.variants}) != len(self.variants):
            raise ValueError("variant ids must be unique")


def _pitch(node: ET.Element, midi: int) -> None:
    if type(midi) is not int or not 0 <= midi <= 127:
        raise ValueError("MIDI pitch must be an integer from 0 to 127")
    names = (
        ("C", 0), ("C", 1), ("D", 0), ("E", -1), ("E", 0), ("F", 0),
        ("F", 1), ("G", 0), ("A", -1), ("A", 0), ("B", -1), ("B", 0),
    )
    step, alter = names[midi % 12]
    pitch = ET.SubElement(node, "pitch")
    ET.SubElement(pitch, "step").text = step
    if alter:
        ET.SubElement(pitch, "alter").text = str(alter)
    ET.SubElement(pitch, "octave").text = str(midi // 12 - 1)


def build_piano_musicxml(
    bars: tuple[tuple[tuple[tuple[int, int], ...], tuple[int, ...]], ...],
    *,
    title: str,
    tempo: int = 84,
    key_fifths: int = 0,
) -> str:
    """Build a bounded two-staff 4/4 piano example from explicit MIDI/durations.

    Each bar is (melody, bass_chord). Melody entries are (midi, duration)
    in quarter-note divisions and must total four. Bass chord pitches sound for
    the full bar. No analytical label is inferred by this builder.
    """

    if not isinstance(title, str) or not title.strip():
        raise ValueError("title is required")
    if type(tempo) is not int or not 20 <= tempo <= 300:
        raise ValueError("tempo must be an integer from 20 to 300")
    if type(key_fifths) is not int or not -7 <= key_fifths <= 7:
        raise ValueError("key_fifths must be from -7 to 7")
    if not isinstance(bars, tuple) or not bars:
        raise ValueError("at least one bar is required")

    root = ET.Element("score-partwise", version="4.0")
    work = ET.SubElement(root, "work")
    ET.SubElement(work, "work-title").text = title
    part_list = ET.SubElement(root, "part-list")

    for part_id, name in (("RH", "Pedagogical piano RH"), ("LH", "Pedagogical piano LH")):
        score_part = ET.SubElement(part_list, "score-part", id=part_id)
        ET.SubElement(score_part, "part-name").text = name
        part = ET.SubElement(root, "part", id=part_id)

        for number, (melody, bass) in enumerate(bars, start=1):
            if not melody or sum(duration for _, duration in melody) != 4:
                raise ValueError("each melody bar must contain exactly four quarter divisions")
            if not bass:
                raise ValueError("each bar requires at least one bass/chord pitch")
            measure = ET.SubElement(part, "measure", number=str(number))
            attrs = ET.SubElement(measure, "attributes")
            ET.SubElement(attrs, "divisions").text = "1"
            key = ET.SubElement(attrs, "key")
            ET.SubElement(key, "fifths").text = str(key_fifths)
            time = ET.SubElement(attrs, "time")
            ET.SubElement(time, "beats").text = "4"
            ET.SubElement(time, "beat-type").text = "4"
            clef = ET.SubElement(attrs, "clef")
            ET.SubElement(clef, "sign").text = "G" if part_id == "RH" else "F"
            ET.SubElement(clef, "line").text = "2" if part_id == "RH" else "4"

            if number == 1:
                direction = ET.SubElement(measure, "direction")
                dtype = ET.SubElement(direction, "direction-type")
                metronome = ET.SubElement(dtype, "metronome")
                ET.SubElement(metronome, "beat-unit").text = "quarter"
                ET.SubElement(metronome, "per-minute").text = str(tempo)
                ET.SubElement(direction, "sound", tempo=str(tempo))

            entries = melody if part_id == "RH" else tuple((midi, 4) for midi in bass)
            for index, (midi, duration) in enumerate(entries):
                if type(duration) is not int or duration not in {1, 2, 4}:
                    raise ValueError("supported durations are quarter, half, or whole")
                note = ET.SubElement(measure, "note", id=f"{part_id}:{number}:n{index + 1}")
                if part_id == "LH" and index:
                    ET.SubElement(note, "chord")
                _pitch(note, midi)
                ET.SubElement(note, "duration").text = str(duration)
                ET.SubElement(note, "voice").text = "1"
                ET.SubElement(note, "staff").text = "1"
                ET.SubElement(note, "type").text = {1: "quarter", 2: "half", 4: "whole"}[duration]

    xml = ET.tostring(root, encoding="unicode")
    parse_score(xml)
    return xml


def _bars(*items):
    return tuple(items)


def _tonicization_vs_modulation() -> TheoryContrastSet:
    c = (48, 52, 55)
    am = (45, 48, 52)
    d = (50, 54, 57)
    d7 = (50, 54, 57, 60)
    g = (43, 47, 50)

    tonicization = _bars(
        (((72, 1), (76, 1), (79, 2)), c),
        (((74, 1), (78, 1), (81, 2)), d),
        (((79, 1), (77, 1), (74, 2)), g),
        (((72, 4),), c),
    )
    modulation = _bars(
        (((72, 1), (76, 1), (79, 2)), c),
        (((69, 1), (72, 1), (76, 2)), am),
        (((74, 1), (78, 1), (81, 2)), d7),
        (((79, 1), (83, 1), (79, 2)), g),
        (((76, 1), (72, 1), (76, 1), (79, 1)), c),
        (((78, 1), (81, 1), (78, 1), (74, 1)), d7),
        (((79, 1), (83, 1), (86, 1), (79, 1)), g),
    )
    return TheoryContrastSet(
        concept="tonicization-vs-modulation",
        objective="Hear and see the difference between a brief applied-dominant tonicization and a cadence-supported move to V.",
        prompt="Which version merely points toward V, and which version actually establishes V as a local tonic?",
        variants=(
            TheoryExampleVariant(
                "tonicization",
                "Tonicization of V",
                "V/V intensifies V, but the phrase returns to the home tonic.",
                build_piano_musicxml(tonicization, title="Tonicization of V"),
                ("home key returns in the final bar", "applied dominant is local evidence, not a new tonic by itself"),
            ),
            TheoryExampleVariant(
                "modulation",
                "Modulation to V",
                "A pivot-compatible sonority leads to V/V, then a G arrival is reinforced by IV-V-I in the new key.",
                build_piano_musicxml(modulation, title="Modulation to V"),
                ("arrival on G is treated as the local tonic goal", "pedagogical model requires contextual review"),
            ),
        ),
    )


def _cadence_vs_dominant_arrival() -> TheoryContrastSet:
    c = (48, 52, 55)
    dm = (50, 53, 57)
    g = (43, 47, 50)
    am = (45, 48, 52)

    cadence = _bars(
        (((74, 1), (72, 1), (69, 2)), dm),
        (((71, 1), (74, 1), (77, 2)), g),
        (((72, 4),), c),
    )
    dominant_arrival = _bars(
        (((76, 1), (74, 1), (72, 2)), am),
        (((74, 1), (71, 1), (74, 2)), g),
        (((76, 1), (74, 1), (72, 2)), am),
    )
    return TheoryContrastSet(
        concept="cadence-vs-dominant-arrival",
        objective="Distinguish a syntactic cadential goal from a dominant boundary that continues the phrase.",
        prompt="Which dominant participates in a completed cadential syntax, and which one is only an arrival before continuation?",
        variants=(
            TheoryExampleVariant(
                "cadence",
                "Cadential progression",
                "A predominant-to-dominant motion resolves to tonic at the end of the unit.",
                build_piano_musicxml(cadence, title="Cadential progression"),
            ),
            TheoryExampleVariant(
                "dominant-arrival",
                "Dominant arrival",
                "The dominant receives emphasis, but the musical process continues rather than closing on tonic.",
                build_piano_musicxml(dominant_arrival, title="Dominant arrival"),
            ),
        ),
    )


def _triad_inversions() -> TheoryContrastSet:
    root = _bars((((72, 1), (76, 1), (79, 1), (76, 1)), (48, 52, 55)))
    first = _bars((((72, 1), (76, 1), (79, 1), (76, 1)), (52, 55, 60)))
    second = _bars((((72, 1), (76, 1), (79, 1), (76, 1)), (55, 60, 64)))
    return TheoryContrastSet(
        concept="triad-inversions",
        objective="Hold chord identity constant while changing only the bass member that determines inversion.",
        prompt="Which chord member is in the bass in each version?",
        variants=(
            TheoryExampleVariant("root-position", "Root position", "C is the lowest chord member.", build_piano_musicxml(root, title="C major root position")),
            TheoryExampleVariant("first-inversion", "First inversion", "E is the lowest chord member.", build_piano_musicxml(first, title="C major first inversion")),
            TheoryExampleVariant("second-inversion", "Second inversion", "G is the lowest chord member.", build_piano_musicxml(second, title="C major second inversion")),
        ),
    )


_CATALOG = {
    "tonicization-vs-modulation": _tonicization_vs_modulation,
    "cadence-vs-dominant-arrival": _cadence_vs_dominant_arrival,
    "triad-inversions": _triad_inversions,
}

_ALIASES = {
    "tonicization": "tonicization-vs-modulation",
    "modulation": "tonicization-vs-modulation",
    "tonicization vs modulation": "tonicization-vs-modulation",
    "modulation to v": "tonicization-vs-modulation",
    "cadence": "cadence-vs-dominant-arrival",
    "dominant arrival": "cadence-vs-dominant-arrival",
    "cadence vs dominant arrival": "cadence-vs-dominant-arrival",
    "inversion": "triad-inversions",
    "triad inversion": "triad-inversions",
    "triad inversions": "triad-inversions",
}


def available_concepts() -> tuple[str, ...]:
    return tuple(sorted(_CATALOG))


def generate_theory_contrast(concept: str) -> TheoryContrastSet:
    if not isinstance(concept, str) or not concept.strip():
        raise ValueError("concept is required")
    key = concept.strip().casefold().replace("_", "-")
    key = _ALIASES.get(key, key)
    factory = _CATALOG.get(key)
    if factory is None:
        raise ValueError(
            "unsupported built-in concept; supply an explicit symbolic teaching model "
            f"or choose one of: {', '.join(available_concepts())}"
        )
    return factory()


def write_contrast_package(
    contrast: TheoryContrastSet,
    destination: Path,
    *,
    render: bool = False,
) -> dict:
    """Persist editable MusicXML and an optional deterministic local engraving."""

    if not isinstance(contrast, TheoryContrastSet):
        raise TypeError("contrast must be a TheoryContrastSet")
    destination = Path(destination).expanduser().resolve()
    if destination.exists():
        raise ValueError("refusing to overwrite an existing contrast package")
    destination.mkdir(parents=True, exist_ok=False)

    manifest = {
        "schema_version": 1,
        "concept": contrast.concept,
        "objective": contrast.objective,
        "prompt": contrast.prompt,
        "status": contrast.status,
        "authority": "assistant_generated_pedagogical_material",
        "course_evidence": False,
        "variants": [],
    }

    for variant in contrast.variants:
        variant_dir = destination / variant.variant_id
        variant_dir.mkdir()
        xml_path = variant_dir / "score.musicxml"
        xml_path.write_text(variant.musicxml, encoding="utf-8")
        item = {
            "variant_id": variant.variant_id,
            "title": variant.title,
            "teaching_point": variant.teaching_point,
            "annotations": list(variant.annotations),
            "status": variant.status,
            "musicxml": str(xml_path),
        }
        if render:
            from tutor_framework.domains.music.global_theory.engraving import engrave_original_score

            render_dir = variant_dir / "rendered"
            rendered = engrave_original_score(
                variant.musicxml,
                destination=render_dir,
                title=variant.title,
            )
            item["rendered"] = {
                "directory": rendered["directory"],
                "provider": rendered["provider"],
                "provider_version": rendered["provider_version"],
                "midi_validation": rendered["midi_validation"],
                "musical_expert_review": rendered["musical_expert_review"],
                "artifact_hashes": rendered["artifact_hashes"],
            }
        manifest["variants"].append(item)

    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    return manifest