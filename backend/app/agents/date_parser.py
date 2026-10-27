"""Reads a preferred appointment date from a chat message.

Understands (all relative to "today in India"):
    tomorrow, day after tomorrow, today
    in 3 days, in 2 weeks, next week
    monday / this friday / next monday
    2026-11-05 (ISO), 05/11/2026, 5-11-2026, 5.11.26  (day first, as in India)
    5 nov, 5th november 2026, november 5, nov 5th

Returns the date and the exact words it used, so the Agent Activity panel
can show what was understood. Whether the date is allowed (tomorrow to 90
days ahead) is checked separately by the appointment service.
"""

import re
from datetime import date, timedelta

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_WEEKDAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
_MONTH_NAMES = "|".join(sorted(_MONTHS, key=len, reverse=True))
_NUMBER_WORDS = {"one": 1, "a": 1, "an": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "ten": 10}

_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_NUMERIC_DMY = re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?\b")
_DAY_MONTH = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?(?: of)? ({_MONTH_NAMES})\b\.?(?:,? (\d{{4}}))?")
_MONTH_DAY = re.compile(rf"\b({_MONTH_NAMES}) (\d{{1,2}})(?:st|nd|rd|th)?\b(?:,? (\d{{4}}))?")
_IN_N = re.compile(r"\bin (\d{1,2}|one|two|three|four|five|six|seven|ten|a|an) (day|days|week|weeks)\b")
_WEEKDAY = re.compile(r"\b(?:(this|next|coming) )?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b")


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _with_year(month: int, day: int, year_text: str | None, today: date) -> date | None:
    if year_text:
        year = int(year_text)
        if year < 100:
            year += 2000
        return _safe_date(year, month, day)
    # No year given: use the next time this date comes round.
    candidate = _safe_date(today.year, month, day)
    if candidate is not None and candidate < today:
        candidate = _safe_date(today.year + 1, month, day)
    return candidate


def parse_preferred_date(normalised_text: str, today: date) -> tuple[date | None, str | None]:
    text = normalised_text

    if re.search(r"\bday after tomorrow\b", text):
        return today + timedelta(days=2), "day after tomorrow"
    if re.search(r"\btomorrow\b", text):
        return today + timedelta(days=1), "tomorrow"
    if re.search(r"\b(today|tonight|right now)\b", text):
        return today, "today"
    if re.search(r"\bnext week\b", text):
        return today + timedelta(days=7), "next week"

    if match := _IN_N.search(text):
        amount = _NUMBER_WORDS.get(match.group(1)) or int(match.group(1))
        days = amount * (7 if match.group(2).startswith("week") else 1)
        return today + timedelta(days=days), match.group(0)

    if match := _ISO.search(text):
        return _safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3))), match.group(0)

    if match := _DAY_MONTH.search(text):
        return _with_year(_MONTHS[match.group(2)], int(match.group(1)), match.group(3), today), match.group(0)

    if match := _MONTH_DAY.search(text):
        return _with_year(_MONTHS[match.group(1)], int(match.group(2)), match.group(3), today), match.group(0)

    if match := _NUMERIC_DMY.search(text):
        day, month = int(match.group(1)), int(match.group(2))
        if 1 <= month <= 12:
            return _with_year(month, day, match.group(3), today), match.group(0)

    if match := _WEEKDAY.search(text):
        # "friday", "this friday", "next friday" all mean the coming Friday.
        # The same weekday as today means one week ahead. The patient sees
        # the exact date in the confirmation card before anything is saved.
        target = _WEEKDAYS[match.group(2)]
        days_ahead = (target - today.weekday()) % 7 or 7
        return today + timedelta(days=days_ahead), match.group(0)

    return None, None
