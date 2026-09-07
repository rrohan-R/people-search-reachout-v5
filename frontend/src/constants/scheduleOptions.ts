// Mirrors app/services/scheduling.py on the backend (which mirrors Hunar's
// own `guardrails` validation). Keep these two lists in sync.
// See: https://api.voice.hunar.ai/docs/external/#core_concepts

export const WEEKDAY_OPTIONS: { value: string; label: string }[] = [
  { value: "MON", label: "Mon" },
  { value: "TUE", label: "Tue" },
  { value: "WED", label: "Wed" },
  { value: "THU", label: "Thu" },
  { value: "FRI", label: "Fri" },
  { value: "SAT", label: "Sat" },
  { value: "SUN", label: "Sun" },
];

export const TIMEZONE_OPTIONS = [
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
];

export const DEFAULT_WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI"];
export const DEFAULT_EARLIEST_TIME = "09:00";
export const DEFAULT_LAST_TIME = "18:00";
export const DEFAULT_TIMEZONE = "Asia/Kolkata";
