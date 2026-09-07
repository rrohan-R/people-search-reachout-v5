"""
Validation and "is it time yet?" helpers for CallSchedule.

The rules here intentionally mirror Hunar's own `guardrails` validation
(see https://api.voice.hunar.ai/docs/external/#core_concepts) so that a
schedule which passes validation here is guaranteed to be accepted when we
eventually forward it as `guardrails` on a Hunar call.
"""
import re
from datetime import datetime, time as dt_time
from typing import List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ALLOWED_WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

# Timezones Hunar currently supports (external API docs, "Timezone
# Configuration" section). Kept as a plain list so validation fails fast
# with a clear message instead of a confusing 400 from Hunar later.
SUPPORTED_TIMEZONES = [
    "Asia/Kolkata",
    "America/New_York",
    "America/Los_Angeles",
    "America/Chicago",
    "America/Denver",
    "America/Detroit",
    "America/Kentucky/Louisville",
    "America/Kentucky/Monticello",
    "America/Indiana/Indianapolis",
    "America/Indiana/Vincennes",
    "America/Indiana/Winamac",
    "America/Indiana/Marengo",
    "America/Indiana/Petersburg",
    "America/Indiana/Vevay",
    "America/Indiana/Tell_City",
    "America/Indiana/Knox",
    "America/Menominee",
    "America/North_Dakota/Center",
    "America/North_Dakota/New_Salem",
    "America/North_Dakota/Beulah",
    "America/Boise",
    "America/Phoenix",
    "America/Anchorage",
    "America/Juneau",
    "America/Sitka",
    "America/Metlakatla",
    "America/Yakutat",
    "America/Nome",
    "America/Adak",
    "Pacific/Honolulu",
    "Asia/Riyadh",
    "Europe/London",
]

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _parse_hhmm(value: str, field: str) -> dt_time:
    if not isinstance(value, str) or not _TIME_RE.match(value):
        raise ValueError(f"{field} must be in HH:MM 24-hour format (e.g. '09:00'), got {value!r}")
    hour, minute = value.split(":")
    return dt_time(int(hour), int(minute))


def validate_guardrails(allowed_days: List[str], earliest_call_time: str, last_call_time: str, timezone: str) -> None:
    """Raises ValueError with a user-facing message if anything is invalid."""
    if timezone not in SUPPORTED_TIMEZONES:
        raise ValueError(
            f"Timezone '{timezone}' isn't one Hunar currently supports. "
            f"Pick one of: {', '.join(SUPPORTED_TIMEZONES)}"
        )

    days = list(dict.fromkeys(allowed_days or []))  # de-dupe, preserve order
    if len(days) != len(allowed_days or []):
        raise ValueError("Duplicate days in allowed_days are not allowed.")
    if len(days) < 3:
        raise ValueError("Pick at least 3 distinct calling days.")
    unknown = [d for d in days if d not in ALLOWED_WEEKDAYS]
    if unknown:
        raise ValueError(f"Unknown day(s) {unknown}; use MON, TUE, WED, THU, FRI, SAT, SUN.")

    earliest = _parse_hhmm(earliest_call_time, "earliest_call_time")
    last = _parse_hhmm(last_call_time, "last_call_time")
    if earliest >= last:
        raise ValueError("earliest_call_time must be strictly before last_call_time.")
    window_minutes = (last.hour * 60 + last.minute) - (earliest.hour * 60 + earliest.minute)
    if window_minutes < 180:
        raise ValueError("The calling window must be at least 3 hours wide.")


def normalize_allowed_days(allowed_days: List[str]) -> List[str]:
    """Store days in weekday order, matching what Hunar itself does."""
    order = {d: i for i, d in enumerate(ALLOWED_WEEKDAYS)}
    return sorted(dict.fromkeys(allowed_days or []), key=lambda d: order.get(d, 99))


def is_within_window(allowed_days: List[str], earliest_call_time: str, last_call_time: str, timezone: str) -> bool:
    """True if right now (in the schedule's own timezone) falls inside its calling window."""
    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        return False
    now = datetime.now(tz)
    today_code = ALLOWED_WEEKDAYS[now.weekday()]
    if today_code not in (allowed_days or []):
        return False
    try:
        earliest = _parse_hhmm(earliest_call_time, "earliest_call_time")
        last = _parse_hhmm(last_call_time, "last_call_time")
    except ValueError:
        return False
    return earliest <= now.time() <= last
