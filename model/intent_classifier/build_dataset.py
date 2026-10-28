"""Build training data for the optional DistilBERT intent classifier.

    backend\\.venv\\Scripts\\python.exe model\\intent_classifier\\build_dataset.py

Sources
- Templates below, filled with Nova Health departments, symptoms, dates and
  conditions (synthetic, written for this project).
- CLINC150 (Larson et al., 2019, CC BY 3.0, https://github.com/clinc/oos-eval):
  its greeting / goodbye / thanks intents become "greeting", "what can I ask
  you" becomes "help", and a sample of everything else (banking, travel,
  small talk, the official out-of-scope set) becomes "out_of_scope".

Output: datasets/processed/intent_train.jsonl and intent_val.jsonl
(gitignored). The test set (model/intent_classifier/test_set.json) is
hand-written and never used here.
"""

import json
import random
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "datasets" / "raw" / "clinc150_data_full.json"
OUT = ROOT / "datasets" / "processed"
CLINC_URL = "https://raw.githubusercontent.com/clinc/oos-eval/master/data/data_full.json"
SEED = 2026
PER_INTENT = 450
# Round 1 used 900, which made out_of_scope ~1/3 of the data; see the Phase 5 report.
CLINC_OUT_OF_SCOPE = 400

sys.path.insert(0, str(ROOT / "backend"))
from app.agents.intent.classifier import INTENTS  # noqa: E402

DEPARTMENTS = ["cardiology", "orthopaedics", "dermatology", "ENT", "paediatrics", "general medicine", "gynaecology",
               "ophthalmology", "the eye department", "the skin doctor", "a heart specialist", "a bone doctor", "the lab"]
SYMPTOMS = ["a mild cough", "fever", "a headache", "back pain", "knee pain", "a skin rash", "itchy skin", "a sore throat",
            "ear pain", "red eyes", "stomach ache", "acidity", "loose motions", "body ache", "a cold", "dizziness",
            "joint pain", "tiredness", "a runny nose", "burning urination", "vomiting", "neck pain"]
DURATIONS = ["since yesterday", "for 3 days", "for two days", "for a week", "since this morning", "for 10 days", "on and off for a month", ""]
DATES = ["tomorrow", "next monday", "on friday", "on 5 november", "next week", "day after tomorrow", "this saturday", "on 12/11"]
CONDITIONS = ["asthma", "diabetes", "malaria", "dengue", "typhoid", "tuberculosis", "glaucoma", "anemia", "migraine",
              "psoriasis", "hepatitis b", "kidney stones", "high blood pressure", "thyroid problems", "arthritis", "gout",
              "chickenpox", "cholera", "eczema", "pneumonia", "stroke", "osteoporosis", "cataract", "lupus"]
REF = ["NH-APT-0003", "NH-APT-0012", "my last request", "my cardiology request", "the appointment I booked"]

TEMPLATES: dict[str, list[str]] = {
    "greeting": ["hi", "hello", "hey there", "good morning", "good evening", "namaste", "hii", "hello nova", "thanks",
                 "thank you so much", "ok thanks", "bye", "goodbye", "see you later", "thanks a lot, bye", "hey", "good afternoon"],
    "help": ["what can you do", "how can you help me", "who are you", "help", "what is this assistant", "what are your features",
             "what kind of questions can i ask", "can you explain what you do", "what services does this chatbot offer",
             "how do i use this assistant", "what are you able to help with", "are you a real person"],
    "hospital_info": ["what should i bring to my appointment", "what documents do i need to carry", "what are the visiting hours",
                      "when can i visit a patient", "what are the opd timings", "what time does the hospital open",
                      "how do i book an appointment", "what is the process to book a consultation", "where is the help desk",
                      "where can i park", "is there a canteen", "where is the pharmacy", "do you accept insurance",
                      "do i need my aadhaar card", "what are the timings of {dept}", "when is {dept} open",
                      "where is the emergency department", "what services does the hospital have", "where is the lab",
                      "what are the lab timings", "how early should i arrive", "is the hospital open on sunday",
                      "what is the hospital address", "where do i collect my blood test report"],
    "department_query": ["which department should i visit for {symptom}", "which doctor should i see for {symptom}",
                         "who should i consult for {symptom}", "what department treats {symptom}", "where should i go for {symptom}",
                         "which specialist is right for {symptom}", "which department should i visit for a consultation",
                         "tell me about {dept}", "where is {dept}", "what does {dept} do", "list all departments",
                         "which clinic handles skin problems", "what is the right department for my child", "which department for eye checkup"],
    "appointment_book": ["i want to book an appointment", "book an appointment with {dept} {date}", "i need an appointment {date}",
                         "can you schedule a consultation with {dept}", "i'd like to see a doctor {date}",
                         "please book me a slot in {dept}", "i want to consult {dept} {date}", "make an appointment for me",
                         "i need to see a dermatologist", "get me an appointment for {symptom}", "book a visit {date}",
                         "request an appointment with {dept}", "i want a new appointment", "schedule me with {dept} {date}"],
    "appointment_status": ["what is the status of my appointment", "show my appointments", "list my requests",
                           "is my appointment confirmed", "has my request been approved yet", "check my bookings",
                           "what happened to {ref}", "status of {ref}", "do i have any pending requests", "view my appointment requests",
                           "is {ref} confirmed yet", "show me all my requests"],
    "appointment_cancel": ["cancel my appointment", "please cancel {ref}", "i want to cancel my request", "withdraw my appointment",
                           "i don't need the appointment anymore", "call off my booking", "delete my appointment request",
                           "cancel the appointment {date}", "i no longer need my {dept} appointment", "remove my booking"],
    "symptom_report": ["i have {symptom} {duration}", "i've got {symptom} {duration}", "i am having {symptom} {duration}",
                       "suffering from {symptom} {duration}", "i feel dizzy and tired", "my knee hurts {duration}",
                       "my child has {symptom} {duration}", "i have had {symptom} {duration}, what should i do",
                       "i'm feeling feverish {duration}", "there is {symptom} {duration}", "my back is paining {duration}",
                       "{symptom} {duration}, should i see a doctor"],
    "health_info": ["what is {condition}", "what are the symptoms of {condition}", "what causes {condition}",
                    "how is {condition} treated", "how is {condition} spread", "how can i prevent {condition}",
                    "is {condition} contagious", "tell me about {condition}", "what are the risk factors for {condition}",
                    "who gets {condition}", "is {condition} hereditary", "what are the complications of {condition}",
                    "how is {condition} diagnosed", "what are the early signs of {condition}", "information about {condition}"],
    "out_of_scope": ["what's the weather today", "who won the cricket match", "tell me a joke", "write a poem", "solve my homework",
                     "what is the capital of japan", "recommend a movie", "what is the bitcoin price", "prescribe something for {symptom}",
                     "what medicine should i take for {symptom}", "what is the dosage of paracetamol", "how many tablets can i take",
                     "do i have {condition}", "is it {condition}", "could it be cancer", "diagnose my {symptom}",
                     "is this a heart attack or gas", "which antibiotic is best", "can you give me a prescription"],
}


def fill(template: str, rng: random.Random) -> str:
    text = template.format(
        dept=rng.choice(DEPARTMENTS), symptom=rng.choice(SYMPTOMS), duration=rng.choice(DURATIONS),
        date=rng.choice(DATES), condition=rng.choice(CONDITIONS), ref=rng.choice(REF),
    )
    text = " ".join(text.split())
    # Light surface variation: casing and punctuation, as users type.
    roll = rng.random()
    if roll < 0.25:
        text = text.capitalize()
    if roll > 0.7:
        text += "?" if text.split()[0] in {"what", "which", "who", "where", "when", "how", "is", "do", "can", "has"} else "."
    return text


def template_examples(rng: random.Random) -> list[dict]:
    rows = []
    for intent, templates in TEMPLATES.items():
        seen: set[str] = set()
        attempts = 0
        while len(seen) < PER_INTENT and attempts < PER_INTENT * 20:
            attempts += 1
            seen.add(fill(rng.choice(templates), rng))
        rows += [{"text": text, "label": intent, "source": "templates"} for text in sorted(seen)]
    return rows


def clinc_examples(rng: random.Random) -> list[dict]:
    if not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {CLINC_URL}")
        with urllib.request.urlopen(CLINC_URL, timeout=60) as response:  # noqa: S310 - fixed https URL
            RAW.write_bytes(response.read())
    data = json.loads(RAW.read_text(encoding="utf-8"))
    pairs = data["train"] + data["val"] + data["oos_train"] + data["oos_val"]
    # Questions about the assistant itself are "help" for Nova Health.
    mapped = {
        "greeting": "greeting", "goodbye": "greeting", "thank_you": "greeting",
        "what_can_i_ask_you": "help", "are_you_a_bot": "help", "who_made_you": "help", "what_is_your_name": "help",
    }
    # Dropped: one-word replies (handled by the conversation context) and CLINC
    # intents whose wording overlaps hospital requests (insurance, schedules,
    # reminders, directions, reservations). Labelling those "out_of_scope"
    # would teach the model that "insurance" or "schedule" means out of scope.
    dropped = {
        "yes", "no", "maybe", "cancel", "repeat",
        "insurance", "insurance_change", "schedule_meeting", "meeting_schedule", "calendar", "calendar_update",
        "reminder", "reminder_update", "directions", "cancel_reservation", "confirm_reservation",
        "accept_reservations", "restaurant_reservation", "how_busy", "date", "time", "timezone",
    }
    rows, other = [], []
    for text, clinc_intent in pairs:
        if clinc_intent in dropped:
            continue
        if clinc_intent in mapped:
            rows.append({"text": text, "label": mapped[clinc_intent], "source": "clinc150"})
        else:
            other.append({"text": text, "label": "out_of_scope", "source": "clinc150"})
    rng.shuffle(other)
    return rows + other[:CLINC_OUT_OF_SCOPE]


def main() -> None:
    rng = random.Random(SEED)
    rows = template_examples(rng) + clinc_examples(rng)
    assert {row["label"] for row in rows} <= set(INTENTS), "unknown label"
    rng.shuffle(rows)
    split = int(len(rows) * 0.9)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, part in (("intent_train.jsonl", rows[:split]), ("intent_val.jsonl", rows[split:])):
        with (OUT / name).open("w", encoding="utf-8") as handle:
            for row in part:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"total": len(rows), "train": split, "val": len(rows) - split,
                      "by_label": dict(Counter(r["label"] for r in rows)), "by_source": dict(Counter(r["source"] for r in rows))}, indent=2))


if __name__ == "__main__":
    main()
