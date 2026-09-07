from typing import List, Optional
import httpx

from app.providers.base import BasePeopleSearchProvider, CandidateResult

PDL_SEARCH_URL = "https://api.peopledatalabs.com/v5/person/search"


class PDLProvider(BasePeopleSearchProvider):
    """
    People Data Labs - Person Search API (Elasticsearch-style query).
    Docs: https://docs.peopledatalabs.com/docs/person-search-api
    """
    name = "PDL"

    def search(self, keywords: List[str], locations: List[str],
               seniority: Optional[str], limit: int = 15) -> List[CandidateResult]:
        if not self.is_configured:
            return self._mock_results(keywords, locations, seniority, limit)

        must = []
        if keywords:
            must.append({
                "bool": {
                    "should": [{"match": {"skills": kw}} for kw in keywords] +
                              [{"match": {"job_title": kw}} for kw in keywords],
                    "minimum_should_match": 1,
                }
            })
        if locations:
            must.append({
                "bool": {
                    "should": [{"match": {"location_name": loc}} for loc in locations],
                    "minimum_should_match": 1,
                }
            })
        if seniority:
            must.append({"match": {"job_title_levels": seniority.lower()}})

        es_query = {"query": {"bool": {"must": must or [{"match_all": {}}]}}}

        try:
            resp = httpx.post(
                PDL_SEARCH_URL,
                headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
                json={"query": es_query, "size": limit, "pretty": False},
                timeout=20.0,
            )
            resp.raise_for_status()
            data = resp.json()
            records = data.get("data", [])
            results = []
            for rec in records:
                results.append(CandidateResult(
                    external_id=rec.get("id"),
                    full_name=rec.get("full_name") or f"{rec.get('first_name', '')} {rec.get('last_name', '')}".strip(),
                    title=rec.get("job_title"),
                    company=rec.get("job_company_name"),
                    location=rec.get("location_name"),
                    linkedin_url=rec.get("linkedin_url"),
                    email=(rec.get("emails") or [{}])[0].get("address") if rec.get("emails") else rec.get("work_email"),
                    phone_number=(rec.get("phone_numbers") or [None])[0],
                    skills=rec.get("skills") or [],
                    raw_profile=rec,
                ))
            return results or self._mock_results(keywords, locations, seniority, limit)
        except Exception as exc:  # noqa: BLE001 - degrade gracefully to demo data
            fallback = self._mock_results(keywords, locations, seniority, limit)
            for r in fallback:
                r["raw_profile"]["provider_error"] = str(exc)
            return fallback
