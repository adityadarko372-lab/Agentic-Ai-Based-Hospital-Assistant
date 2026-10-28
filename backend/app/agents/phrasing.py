"""Optional AI rewording of some replies with a local Ollama model (Phase 5).

LLM_PHRASING_ENABLED=true lets a small local model (default qwen2.5:3b) make
a template reply sound more natural. It is deliberately narrow:

- Only "answered" replies from the Patient Assistance and Health Information
  agents. Emergency, care-navigation and appointment replies are NEVER
  reworded: their exact wording is part of the safety design.
- Only the short reply sentence is reworded. Cards (lists, passages,
  numbers) are shown exactly as the agents produced them.
- The rewrite is rejected, and the template kept, if it adds or drops any
  number (times, extensions, phone numbers), uses medical-advice words the
  original did not, adds a link, or is much longer. The guard cannot catch
  every change of meaning (for example "near" becoming "next to"), which is
  why this feature is off by default and limited to non-clinical replies. A timeout (8 s) or a stopped Ollama also keeps
  the template. Every outcome is written to the trace.
- Only a local Ollama address is accepted, so no text leaves the computer.
"""

import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

from app.agents.base import HEALTH_INFO, PATIENT_ASSISTANCE, AgentResult, Trace
from app.core.config import get_settings

PHRASER = "Phrasing (local LLM)"
ELIGIBLE_AGENTS = {PATIENT_ASSISTANCE, HEALTH_INFO}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}

PROMPT = (
    "Rewrite the assistant message below so it sounds friendly and natural for a hospital patient in India. "
    "Rules: keep every fact exactly; do not add facts, numbers, times, phone numbers, advice, diagnoses, medicines or promises; "
    "keep it under 60 words; reply with the rewritten message only.\n\nMessage: {reply}"
)

_NUMBER = re.compile(r"\d+")
# "9:00 AM" and "9 AM" are the same time, so ":00" is ignored when comparing.
_WHOLE_HOUR = re.compile(r":00\b")


def _numbers(text: str) -> set[str]:
    return set(_NUMBER.findall(_WHOLE_HOUR.sub("", text)))
_RISKY_WORDS = re.compile(
    r"\b(diagnos\w*|prescri\w*|dose|dosage|mg|tablet\w*|medicine\w*|antibiotic\w*|cure\w*|guarantee\w*|confirmed|definitely|you have)\b",
    re.IGNORECASE,
)
_LINK = re.compile(r"https?://|www\.", re.IGNORECASE)


def check_rewrite(original: str, rewrite: str) -> str | None:
    """Return why a rewrite is unsafe, or None if it may be used."""
    if not rewrite.strip():
        return "empty answer"
    if len(rewrite) > 2 * len(original) + 60:
        return "much longer than the original"
    original_numbers, rewrite_numbers = _numbers(original), _numbers(rewrite)
    new_numbers = rewrite_numbers - original_numbers
    if new_numbers:
        return f"added numbers not in the original ({', '.join(sorted(new_numbers))})"
    # Times, extensions and phone numbers must all survive the rewrite.
    dropped = original_numbers - rewrite_numbers
    if dropped:
        return f"dropped numbers from the original ({', '.join(sorted(dropped))})"
    original_risky = {word.lower() for word in _RISKY_WORDS.findall(original)}
    new_risky = {word.lower() for word in _RISKY_WORDS.findall(rewrite)} - original_risky
    if new_risky:
        return f"added medical or promise words ({', '.join(sorted(new_risky))})"
    if _LINK.search(rewrite) and not _LINK.search(original):
        return "added a link"
    return None


def _call_ollama(url: str, model: str, prompt: str, timeout: float) -> str:
    body = json.dumps(
        {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2, "num_predict": 120}}
    ).encode("utf-8")
    request = urllib.request.Request(f"{url.rstrip('/')}/api/generate", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - local URL checked by caller
        return str(json.loads(response.read().decode("utf-8")).get("response", "")).strip().strip('"')


def maybe_rephrase(result: AgentResult, trace: Trace) -> bool:
    """Reword result.reply in place when allowed and safe. Returns True if reworded."""
    settings = get_settings()
    if not settings.llm_phrasing_enabled:
        return False
    if result.agent not in ELIGIBLE_AGENTS or result.outcome_status != "answered":
        trace.add(PHRASER, "rephrase_reply", f"Not reworded: {result.agent} replies keep their exact template wording")
        return False
    if urlparse(settings.ollama_url).hostname not in LOCAL_HOSTS:
        trace.add(PHRASER, "rephrase_reply", "Not reworded: OLLAMA_URL is not a local address", status="blocked")
        return False

    original = result.reply
    try:
        rewrite = _call_ollama(settings.ollama_url, settings.ollama_model, PROMPT.format(reply=original), settings.llm_timeout_seconds)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        trace.add(PHRASER, "rephrase_reply", f"Kept the template: Ollama unavailable ({type(error).__name__})", status="fallback")
        return False

    problem = check_rewrite(original, rewrite)
    if problem:
        trace.add(PHRASER, "rephrase_reply", f"Kept the template: rewrite rejected, {problem}", status="fallback", data={"rejected": rewrite[:300]})
        return False
    result.reply = rewrite
    trace.add(
        PHRASER,
        "rephrase_reply",
        f"Reworded by local model {settings.ollama_model}; facts unchanged (no new numbers or medical terms)",
        data={"original": original, "model": settings.ollama_model},
    )
    return True
