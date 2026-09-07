from typing import List, Optional
import httpx

from app.providers.base import BasePeopleSearchProvider, CandidateResult

PROXYCURL_SEARCH_URL = "https://nubela.co/proxycurl/api/v2/search/person/"


class ProxycurlProvider(BasePeopleSearchProvider):
    """
    Proxycurl - Person Search API.
    Docs: https://nubela.co/proxycurl/docs#people-api-person-search-api
    """
    name = "PROXYCURL"

    def search(self, keywords: List[str], locations: List[str],
               seniority: Optional[str], limit: int = 15) -> List[CandidateResult]:
        if not self.is_configured:
            return self._mock_results(keywords, locations, seniority, limit)

        params = {
            "current_role_title": keywords[0] if keywords else None,
            "country": None,
            "page_size": limit,
            "enrich_profiles": "enrich",
        }
        if locations:
            params["region"] = locations[0]
        if seniority:
            params["current_role_title"] = f"{seniority} {params.get('current_role_title') or ''}".strip()
        params = {k: v for k, v in params.items() if v}

        try:
            resp = httpx.get(
                PROXYCURL_SEARCH_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                params=params,
                timeout=25.0,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for entry in data.get("results", [])[:limit]:
                profile = entry.get("profile") or {}
                exp = (profile.get("experiences") or [{}])[0]
                results.append(CandidateResult(
                    external_id=entry.get("linkedin_profile_url"),
                    full_name=profile.get("full_name") or f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip(),
                    title=exp.get("title") or profile.get("occupation"),
                    company=exp.get("company"),
                    location=profile.get("city") or profile.get("country_full_name"),
                    linkedin_url=entry.get("linkedin_profile_url"),
                    email=None,
                    phone_number=None,
                    skills=profile.get("skills") or [],
                    raw_profile=entry,
                ))
            return results or self._mock_results(keywords, locations, seniority, limit)
        except Exception as exc:  # noqa: BLE001
            fallback = self._mock_results(keywords, locations, seniority, limit)
            for r in fallback:
                r["raw_profile"]["provider_error"] = str(exc)
            return fallback
