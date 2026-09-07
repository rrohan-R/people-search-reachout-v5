from typing import List, Optional
import httpx

from app.providers.base import BasePeopleSearchProvider, CandidateResult

APOLLO_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/search"


class ApolloProvider(BasePeopleSearchProvider):
    """
    Apollo.io - People Search API.
    Docs: https://docs.apollo.io/reference/people-search
    """
    name = "APOLLO"

    def search(self, keywords: List[str], locations: List[str],
               seniority: Optional[str], limit: int = 15) -> List[CandidateResult]:
        if not self.is_configured:
            return self._mock_results(keywords, locations, seniority, limit)

        payload = {
            "api_key": self.api_key,
            "q_keywords": " ".join(keywords) if keywords else None,
            "person_locations": locations or None,
            "person_seniorities": [seniority.lower()] if seniority else None,
            "page": 1,
            "per_page": limit,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            resp = httpx.post(
                APOLLO_SEARCH_URL,
                headers={
                    "X-Api-Key": self.api_key,
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                },
                json=payload,
                timeout=20.0,
            )
            resp.raise_for_status()
            data = resp.json()
            people = data.get("people", [])
            results = []
            for p in people:
                org = p.get("organization") or {}
                results.append(CandidateResult(
                    external_id=p.get("id"),
                    full_name=p.get("name"),
                    title=p.get("title"),
                    company=org.get("name"),
                    location=", ".join(filter(None, [p.get("city"), p.get("state"), p.get("country")])),
                    linkedin_url=p.get("linkedin_url"),
                    email=p.get("email"),
                    phone_number=(p.get("phone_numbers") or [{}])[0].get("sanitized_number")
                    if p.get("phone_numbers") else None,
                    skills=[],
                    raw_profile=p,
                ))
            return results or self._mock_results(keywords, locations, seniority, limit)
        except Exception as exc:  # noqa: BLE001
            fallback = self._mock_results(keywords, locations, seniority, limit)
            for r in fallback:
                r["raw_profile"]["provider_error"] = str(exc)
            return fallback
