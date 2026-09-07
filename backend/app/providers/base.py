import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

FIRST_NAMES = ["Ava", "Liam", "Noah", "Emma", "Oliver", "Sophia", "Elijah", "Mia",
               "James", "Amelia", "Arjun", "Priya", "Rohan", "Ananya", "Wei", "Carlos"]
LAST_NAMES = ["Johnson", "Williams", "Brown", "Davis", "Miller", "Wilson", "Moore",
              "Taylor", "Anderson", "Sharma", "Patel", "Nair", "Rao", "Chen", "Garcia"]


class CandidateResult(dict):
    """Simple typed-dict-like structure for a normalized candidate record."""


class BasePeopleSearchProvider(ABC):
    name: str = "BASE"

    def __init__(self, api_key: Optional[str]):
        self.api_key = api_key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @abstractmethod
    def search(self, keywords: List[str], locations: List[str],
               seniority: Optional[str], limit: int = 15) -> List[CandidateResult]:
        ...

    # ---- shared helpers ----

    def _mock_results(self, keywords: List[str], locations: List[str],
                       seniority: Optional[str], limit: int) -> List[CandidateResult]:
        """
        Deterministic-ish mock/demo data generator used when a provider API key
        is not configured, or when the live call fails. Lets the app be fully
        demoable end to end without any external credentials.
        """
        results = []
        role = (keywords[0].title() if keywords else "Professional")
        title_suffix = f"{seniority} {role}" if seniority else role
        for i in range(limit):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            loc = random.choice(locations) if locations else random.choice(
                ["Remote", "Bangalore", "San Francisco", "New York", "London"]
            )
            results.append(CandidateResult(
                external_id=f"{self.name.lower()}-mock-{i}-{first.lower()}{last.lower()}",
                full_name=f"{first} {last}",
                title=title_suffix,
                company=f"{random.choice(['Nimbus', 'Vertex', 'Bluepeak', 'Orbital', 'Northwind'])} "
                        f"{random.choice(['Labs', 'Tech', 'Systems', 'Inc.', 'Solutions'])}",
                location=loc,
                linkedin_url=f"https://linkedin.com/in/{first.lower()}-{last.lower()}-{i}",
                email=f"{first.lower()}.{last.lower()}@example.com",
                phone_number=None,  # left blank; enter manually or via a real provider before calling
                skills=keywords[:6],
                raw_profile={"mock": True, "provider": self.name},
            ))
        return results
