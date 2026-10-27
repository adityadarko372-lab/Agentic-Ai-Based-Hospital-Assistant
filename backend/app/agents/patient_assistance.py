"""Patient Assistance Agent: answers hospital-service and department questions.

It only uses the fictional hospital directory (hospital_info.json and the
departments table). If a question is not covered there, it says so and points
to the help desk instead of guessing.
"""

import re

from app.agents.base import PATIENT_ASSISTANCE, AgentContext, AgentResult, Suggestion
from app.agents.department_matcher import match_departments
from app.knowledge import load_hospital_info

# Topic -> patterns, in priority order (first match wins).
_TOPICS: list[tuple[str, list[str]]] = [
    ("what_to_bring", [r"\b(bring|carry)\b", r"\b(documents|papers|id proof|aadhaar)\b"]),
    ("how_to_book", [r"\bhow (do|can|should) i (book|make|get|request)\b", r"\b(process|steps|procedure)\b.*\b(book|appointment)", r"\bhow to book\b"]),
    ("visiting_hours", [r"\bvisit(ing|or|ors)?\b.*\b(hours?|time|timings|rules|patient)\b", r"\bvisiting\b"]),
    ("emergency_info", [r"\bemergency\b", r"\bcasualty\b", r"\bambulance\b"]),
    ("help_desk", [r"\b(help ?desk|reception|enquiry|inquiry|address|parking)\b", r"\bwhere is (the |nova )?hospital\b"]),
    ("department", []),  # handled with the department matcher
    ("which_department", [r"\bwhich (department|doctor|specialist|clinic)\b", r"\b(right|correct|best) (department|doctor|specialist)\b", r"\b(who|where) should i (see|go|visit|consult)\b", r"\bwhat department\b"]),
    ("opd_hours", [r"\b(opd|opening|working|clinic) (hours|time|timings)\b", r"\b(timings?|hours)\b", r"\bwhat time\b", r"\bwhen\b.*\bopen\b"]),
    ("services_overview", [r"\bservices?\b", r"\b(list|all|what) (of )?(the )?departments\b", r"\bdepartments\b"]),
]


def _source_label() -> str:
    info = load_hospital_info()
    return f"Nova Health demo directory (hospital_info.json, version {info['version']}), fictional content"


def _department_card(record: dict) -> dict:
    return {
        "type": "department",
        "department": {key: record[key] for key in ("id", "name", "summary", "location", "opening_hours", "extension", "accepts_appointments", "icon", "category")},
    }


def _detect_topic(text: str) -> str | None:
    for topic, patterns in _TOPICS:
        if any(re.search(pattern, text) for pattern in patterns):
            return topic
    return None


def handle(ctx: AgentContext) -> AgentResult:
    info = load_hospital_info()
    hospital = info["hospital"]
    departments = {record["id"]: record for record in info["departments"]}
    guidance = info["appointment_guidance"]
    source = _source_label()

    matches = match_departments(ctx.text)
    topic = _detect_topic(ctx.text)
    # A named department (or a body area) answers "where/when is X" questions directly,
    # unless the question is clearly about something general (what to bring, booking steps...).
    if matches and topic in (None, "department", "which_department", "opd_hours", "services_overview"):
        topic = "department"

    ctx.trace.add(
        PATIENT_ASSISTANCE,
        "identify_topic",
        f"Topic: {topic or 'not recognised'}"
        + (f"; departments mentioned: {', '.join(departments[m.department_id]['name'] for m in matches)}" if matches else ""),
        data={"topic": topic, "departments": [{"id": m.department_id, "matched": m.matched, "kind": m.kind} for m in matches]},
    )

    def answered(reply: str, summary: str, cards: list[dict], suggestions: list[Suggestion]) -> AgentResult:
        ctx.trace.add(PATIENT_ASSISTANCE, "lookup_directory", f"Answered from the hospital directory: {summary}", data={"source": source})
        return AgentResult(PATIENT_ASSISTANCE, reply, "answered", summary, cards, suggestions, [source])

    if topic == "what_to_bring":
        return answered(
            "Here is what to bring to your appointment at Nova Health. " + guidance["arrival_advice"],
            "Listed what to bring to an appointment",
            [{"type": "checklist", "title": "What to bring", "items": guidance["what_to_bring"]}],
            [Suggestion("Book an appointment", message="I want to book an appointment"), Suggestion("OPD timings", message="What are the OPD timings?")],
        )

    if topic == "how_to_book":
        return answered(
            "You can request an appointment in two ways: through the Appointments page, or right here in this chat. "
            "Either way, the request is saved as Pending until the hospital reviews it.",
            "Explained how to request an appointment",
            [{"type": "steps", "title": "How booking works", "items": guidance["how_to_book"]}],
            [Suggestion("Book an appointment now", message="I want to book an appointment"), Suggestion("Open the appointment form", href="/appointments")],
        )

    if topic == "visiting_hours":
        return answered(
            f"Visiting hours: {hospital['visiting_hours']}. Please check with the ward staff, as rules can differ for intensive care.",
            "Gave visiting hours",
            [],
            [Suggestion("Where is the help desk?", message="Where is the help desk?")],
        )

    if topic == "emergency_info":
        emergency = departments["emergency"]
        return answered(
            "For a medical emergency, call 112 (national emergency) or 108 (ambulance), or go directly to the Emergency "
            f"Department. It is {emergency['opening_hours'].lower()}, at {emergency['location']}. You do not need an appointment.",
            "Explained how to reach emergency care",
            [_department_card(emergency)],
            [Suggestion("Check my symptoms", href="/symptom-guidance")],
        )

    if topic == "help_desk":
        return answered(
            f"The help desk is at the {hospital['help_desk']}. Staff there can help with registration, directions and questions "
            f"I cannot answer. Outpatient (OPD) hours: {hospital['opd_hours']}.",
            "Gave help desk location",
            [],
            [Suggestion("Show hospital services", message="Where can I find hospital services?")],
        )

    if topic == "department" and matches:
        shown = [departments[m.department_id] for m in matches[:3]]
        first = shown[0]
        via_keyword = matches[0].kind == "keyword"
        if via_keyword:
            reply = (
                f"For concerns related to “{matches[0].matched}”, {first['name']} is usually the relevant department. "
                "This is directions only, not a diagnosis. If you are unsure, General Medicine can see you first."
            )
        else:
            reply = f"{first['name']} is at {first['location']}. Hours: {first['opening_hours']} ({first['extension']})."
        if not first["accepts_appointments"]:
            reply += " No appointment is needed here."
        suggestions = []
        if first["accepts_appointments"]:
            suggestions.append(Suggestion(f"Book {first['name']}", message=f"I want to book an appointment with {first['name']}"))
            suggestions.append(Suggestion("Open the form", href=f"/appointments?department={first['id']}"))
        if via_keyword:
            suggestions.append(Suggestion("How urgent is it?", href="/symptom-guidance"))
        return answered(reply, f"Gave directions to {', '.join(d['name'] for d in shown)}", [_department_card(d) for d in shown], suggestions)

    if topic == "which_department":
        general = departments["general-medicine"]
        clinical = [d for d in info["departments"] if d["category"] == "clinical"]
        return answered(
            "If you are not sure where to go, start with General Medicine. It is the first point of contact for most "
            f"concerns and can refer you to a specialist. It is at {general['location']} ({general['opening_hours']}). "
            "Tell me your concern (for example “knee pain” or “skin rash”) and I can point you to a department.",
            "Recommended General Medicine as the first point of contact",
            [_department_card(general), {"type": "departments", "title": "All clinical departments", "items": [_department_card(d)["department"] for d in clinical]}],
            [
                Suggestion("Book General Medicine", message="I want to book an appointment with General Medicine"),
                Suggestion("Which department for knee pain?", message="Which department should I visit for knee pain?"),
            ],
        )

    if topic == "opd_hours":
        return answered(
            f"Outpatient (OPD) hours are {hospital['opd_hours']}. The Emergency Department is {hospital['emergency_hours'].lower()}. "
            "Individual departments may differ; ask me about a department for its exact timings.",
            "Gave OPD hours",
            [],
            [Suggestion("Cardiology timings", message="What are the timings of Cardiology?"), Suggestion("What should I bring?", message="What should I bring to my appointment?")],
        )

    if topic == "services_overview":
        return answered(
            f"Here are the departments and services at {hospital['name']} with where to find them. "
            f"The help desk is at the {hospital['help_desk']}.",
            "Listed hospital departments and services",
            [{"type": "departments", "title": "Departments and services", "items": [_department_card(d)["department"] for d in info["departments"]]}],
            [Suggestion("Which department should I visit?", message="Which department should I visit for a consultation?"), Suggestion("Open Hospital Services", href="/services")],
        )

    # Nothing in the directory covers this question: say so, do not guess.
    ctx.trace.add(PATIENT_ASSISTANCE, "lookup_directory", "No verified information found for this question", status="warning")
    return AgentResult(
        PATIENT_ASSISTANCE,
        "I don't have verified information about that in the Nova Health directory, so I won't guess. "
        f"The help desk at the {hospital['help_desk']} can help.",
        "information_unavailable",
        "Question not covered by the hospital directory",
        [],
        [Suggestion("Show hospital services", message="Where can I find hospital services?"), Suggestion("What can you do?", message="What can you help with?")],
        [source],
    )

