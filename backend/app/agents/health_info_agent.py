"""Health Information Agent (optional, Phase 5): general educational facts.

Answers general questions such as "what is asthma?" or "how is malaria
spread?" with a passage from the NIH MedQuAD collection (CC BY 4.0), always
cited and labelled as general information, not advice about the patient.

It never guesses:
- feature switched off            -> says so ("information_unavailable")
- index or libraries not installed -> says so, with the reason in the trace
- best match below the threshold   -> "no reliable answer", no passage shown
Diagnosis and medicine questions never reach this agent: the rule classifier
labels them out_of_scope, and the Safety Gate runs before everything.
"""

from app.agents.base import HEALTH_INFO, AgentContext, AgentResult, Suggestion
from app.core.config import get_settings
from app.health_info.medquad import excerpt
from app.health_info.retriever import Unavailable, get_retriever

DISCLAIMER = (
    "General educational information from the U.S. National Institutes of Health (via MedQuAD). "
    "It is not medical advice, is not about your situation, and may not match practice in India. "
    "For your own symptoms, use Symptom Guidance or see a doctor. In an emergency call 112 or 108."
)
LICENSE = "MedQuAD, CC BY 4.0 (Ben Abacha & Demner-Fushman, 2019)"

FOLLOW_UPS = [
    Suggestion("Get symptom guidance", href="/symptom-guidance"),
    Suggestion("Which department?", message="Which department should I visit for a consultation?"),
    Suggestion("Book an appointment", message="I want to book an appointment"),
]


def _unavailable(ctx: AgentContext, detail: str, summary: str) -> AgentResult:
    ctx.trace.add(HEALTH_INFO, "search_medquad", detail, status="fallback")
    return AgentResult(
        HEALTH_INFO,
        "I can't look up general health information right now. "
        "I can still help you find the right department, request an appointment, or give preliminary guidance on where to seek care.",
        "information_unavailable",
        summary,
        suggestions=FOLLOW_UPS,
    )


def handle(ctx: AgentContext) -> AgentResult:
    settings = get_settings()
    if not settings.health_info_enabled:
        return _unavailable(ctx, "Health information is switched off (HEALTH_INFO_ENABLED=false)", "General health information is switched off")

    retriever = get_retriever()
    if isinstance(retriever, Unavailable):
        return _unavailable(ctx, f"MedQuAD search unavailable: {retriever.reason}", "General health information is not installed")

    hits = retriever.search(ctx.message, k=3)
    top = [{"question": hit.record["question"], "source": hit.record["source"], "score": round(hit.score, 3)} for hit in hits]
    best = hits[0] if hits else None
    threshold = settings.health_info_min_score

    if best is None or best.score < threshold:
        ctx.trace.add(
            HEALTH_INFO,
            "search_medquad",
            f"No reliable match (best similarity {best.score:.2f} < {threshold:.2f})" if best else "No match",
            status="warning",
            data={"top_matches": top, "threshold": threshold, "retriever": retriever.name},
        )
        return AgentResult(
            HEALTH_INFO,
            "I couldn't find a reliable answer to that in the NIH MedQuAD collection, so I won't guess. "
            "A doctor can answer it properly. I can help you find the right department or request an appointment.",
            "information_unavailable",
            f"No reliable MedQuAD match (best {best.score:.2f})" if best else "No MedQuAD match",
            suggestions=FOLLOW_UPS,
        )

    record = best.record
    ctx.trace.add(
        HEALTH_INFO,
        "search_medquad",
        f"Matched \u201c{record['question']}\u201d from {record['source']} (similarity {best.score:.2f} \u2265 {threshold:.2f})",
        data={"top_matches": top, "threshold": threshold, "retriever": retriever.name, "qtype": record["qtype"]},
    )
    source = f"{record['source']} via MedQuAD ({LICENSE}): {record['url']}"
    return AgentResult(
        HEALTH_INFO,
        f"Here is general information about {record['focus']} from {record['source']} (NIH). It is not medical advice.",
        "answered",
        f"Shared general information on {record['focus']} ({record['source']}, similarity {best.score:.2f})",
        [
            {
                "type": "health_info",
                "title": record["focus"],
                "question": record["question"],
                "answer": excerpt(record["answer"]),
                "source": record["source"],
                "url": record["url"],
                "similarity": round(best.score, 3),
                "license": LICENSE,
                "disclaimer": DISCLAIMER,
            }
        ],
        FOLLOW_UPS,
        [source],
    )
