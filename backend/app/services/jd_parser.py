
import re
from typing import List, Optional, Tuple

SKILL_VOCAB = [
    "python", "java", "javascript", "typescript", "react", "angular", "vue",
    "node.js", "node", "django", "flask", "fastapi", "spring", "kubernetes",
    "docker", "aws", "azure", "gcp", "terraform", "sql", "postgres", "mysql",
    "mongodb", "redis", "kafka", "spark", "hadoop", "machine learning", "ml",
    "deep learning", "nlp", "computer vision", "data science", "data engineering",
    "product management", "product manager", "ui/ux", "figma", "sales",
    "business development", "marketing", "seo", "sem", "content marketing",
    "recruiting", "talent acquisition", "hr", "finance", "accounting",
    "salesforce", "hubspot", "customer success", "account management",
    "go", "golang", "rust", "c++", "c#", ".net", "ruby", "rails", "php",
    "swift", "kotlin", "android", "ios", "graphql", "rest api", "microservices",
    "devops", "ci/cd", "security", "cybersecurity", "blockchain", "solidity",
]

SENIORITY_VOCAB = [
    ("intern", "Intern"),
    ("entry level", "Entry Level"),
    ("junior", "Junior"),
    ("associate", "Associate"),
    ("mid level", "Mid-Level"),
    ("senior", "Senior"),
    ("staff", "Staff"),
    ("principal", "Principal"),
    ("lead", "Lead"),
    ("manager", "Manager"),
    ("director", "Director"),
    ("vp", "VP"),
    ("vice president", "VP"),
    ("head of", "Head"),
    ("chief", "C-Level"),
    ("cto", "C-Level"),
    ("ceo", "C-Level"),
]

# A short list of well-known cities/regions to opportunistically detect. This
# is not exhaustive -- the UI lets users add/edit locations directly too.
LOCATION_VOCAB = [
    "remote", "hybrid", "san francisco", "new york", "los angeles", "seattle",
    "austin", "boston", "chicago", "denver", "atlanta", "miami", "london",
    "berlin", "amsterdam", "paris", "dublin", "toronto", "vancouver",
    "bangalore", "bengaluru", "mumbai", "delhi", "gurgaon", "gurugram",
    "hyderabad", "pune", "chennai", "kochi", "singapore", "dubai", "sydney",
    "melbourne", "tokyo",
]


def _find_title_line(text: str) -> Optional[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None
    # Heuristic: title is usually the first short-ish line
    first = lines[0]
    if len(first) <= 90:
        return first
    return None


def extract_keywords(text: str) -> List[str]:
    lowered = text.lower()
    found = []
    for skill in SKILL_VOCAB:
        if re.search(r"(?<![a-z])" + re.escape(skill) + r"(?![a-z])", lowered):
            found.append(skill)
    # de-dup while preserving order, cap to a reasonable number
    seen = set()
    result = []
    for k in found:
        if k not in seen:
            seen.add(k)
            result.append(k)
    return result[:20]


def extract_locations(text: str) -> List[str]:
    lowered = text.lower()
    found = []
    for loc in LOCATION_VOCAB:
        if loc in lowered:
            found.append(loc.title() if loc not in ("remote", "hybrid") else loc.title())
    seen = set()
    result = []
    for l in found:
        if l not in seen:
            seen.add(l)
            result.append(l)
    return result[:10]


def extract_seniority(text: str) -> Optional[str]:
    lowered = text.lower()
    for needle, label in SENIORITY_VOCAB:
        if needle in lowered:
            return label
    return None


def extract_company_hint(text: str) -> Optional[str]:
    m = re.search(r"(?:at|for|with)\s+([A-Z][A-Za-z0-9&.\-]{1,40})\b", text)
    if m:
        return m.group(1)
    return None


def parse_job_description(title: str, raw_text: str) -> Tuple[List[str], List[str], Optional[str], Optional[str]]:
    """Returns (keywords, locations, seniority, company_hint)."""
    combined = f"{title}\n{raw_text}"
    keywords = extract_keywords(combined)
    if not keywords:
        # fall back to naive noun-ish tokens from the title
        keywords = [w.strip(",.") for w in title.split() if len(w) > 3][:8]
    locations = extract_locations(combined)
    seniority = extract_seniority(combined)
    company_hint = extract_company_hint(raw_text)
    return keywords, locations, seniority, company_hint
