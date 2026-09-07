// Enum values accepted by the Hunar Voice Agents API for agent creation.
// See: https://api.voice.hunar.ai/docs/external/

export const LANGUAGE_OPTIONS = [
  "ENGLISH",
  "HINDI",
  "TAMIL",
  "TELUGU",
  "KANNADA",
  "MARATHI",
  "MALAYALAM",
  "GUJARATI",
  "BENGALI",
  "TURKISH",
  "ARABIC",
  "SPANISH",
];

export const VOICE_PERSONA_OPTIONS = ["NEHA", "ROY", "ZOE", "SAM", "MIRA", "EESHA"];

export const ANSWER_TYPE_OPTIONS: { value: "string" | "boolean" | "number"; label: string }[] = [
  { value: "string", label: "Text answer" },
  { value: "boolean", label: "Yes / No" },
  { value: "number", label: "Number" },
];
