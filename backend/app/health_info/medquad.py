"""Parse MedQuAD XML files into clean question/answer records.

MedQuAD (Ben Abacha & Demner-Fushman, 2019; CC BY 4.0) contains 47,457
question/answer pairs from 12 NIH websites. Answers were removed from three
collections (A.D.A.M., MedlinePlus Herbs and MedlinePlus Drugs) for copyright
reasons, so those pairs have no answer and are dropped here.

We also drop medicine-specific question types (dosage, side effects, ...):
Nova Health does not give medication advice, even general.
"""

import re
from dataclasses import asdict, dataclass

try:  # defusedxml blocks entity-expansion tricks in downloaded XML.
    from defusedxml.ElementTree import fromstring as parse_xml
except ImportError:  # pragma: no cover - optional dependency
    from xml.etree.ElementTree import fromstring as parse_xml

# Question types that are about specific medicines: never served.
EXCLUDED_QTYPES = frozenset(
    {
        "brand names",
        "brand names of combination products",
        "contraindication",
        "dietary",
        "dosage",
        "emergency or overdose",
        "forget a dose",
        "how can i learn more",
        "how does it work",
        "how effective is it",
        "indication",
        "interactions with foods",
        "interactions with herbs and supplements",
        "interactions with medications",
        "other information",
        "precautions",
        "severe reaction",
        "side effects",
        "special instructions",
        "storage and disposal",
        "usage",
        "why get vaccinated",
    }
)

# Very short answers are usually "See the ... page" stubs.
MIN_ANSWER_CHARS = 80

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class MedQuADRecord:
    id: str  # question id, e.g. "0000001-1"
    focus: str  # the topic, e.g. "Asthma"
    question: str
    qtype: str
    answer: str
    source: str  # e.g. "MedlinePlus", "CancerGov"
    url: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _clean(text: str | None) -> str:
    return _WHITESPACE.sub(" ", text or "").strip()


def _clean_question(text: str) -> str:
    # MedQuAD's generated questions read "What is (are) Asthma ?"
    text = text.replace("(are) ", "").replace(" ?", "?")
    return _clean(text)


def parse_document(xml_text: str) -> list[MedQuADRecord]:
    """Return the usable records of one MedQuAD XML document."""
    root = parse_xml(xml_text)
    source = _clean(root.get("source"))
    url = _clean(root.get("url"))
    focus = _clean(root.findtext("Focus"))
    records: list[MedQuADRecord] = []
    for pair in root.iter("QAPair"):
        question_el = pair.find("Question")
        if question_el is None:
            continue
        qtype = _clean(question_el.get("qtype")).lower()
        answer = _clean(pair.findtext("Answer"))
        if qtype in EXCLUDED_QTYPES or len(answer) < MIN_ANSWER_CHARS:
            continue
        records.append(
            MedQuADRecord(
                id=_clean(question_el.get("qid")),
                focus=focus,
                question=_clean_question(question_el.text or ""),
                qtype=qtype,
                answer=answer,
                source=source,
                url=url,
            )
        )
    return records


def dedupe(records: list[MedQuADRecord]) -> list[MedQuADRecord]:
    """Keep the first record for each (question, answer-start) pair."""
    seen: set[tuple[str, str]] = set()
    unique: list[MedQuADRecord] = []
    for record in records:
        key = (record.question.lower(), record.answer[:200].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def excerpt(answer: str, limit: int = 900) -> str:
    """Shorten an answer at a sentence boundary so the card stays readable."""
    if len(answer) <= limit:
        return answer
    cut = answer[:limit]
    boundary = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    if boundary > limit * 0.5:
        return cut[: boundary + 1]
    return cut.rsplit(" ", 1)[0] + "…"
