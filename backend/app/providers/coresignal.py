from typing import List, Optional
import httpx

from app.providers.base import BasePeopleSearchProvider, CandidateResult

CORESIGNAL_SEARCH_URL = "https://api.coresignal.com/cdapi/v1/professional_network/employee/search/es_dsl"
CORESIGNAL_COLLECT_URL = "https://api.coresignal.com/cdapi/v1/professional_network/employee/collect/{id}"


class CoresignalProvider(BasePeopleSearchProvider):
    """
    Coresignal - Employee Multi-source search (Elasticsearch DSL) + collect.
    Docs: https://docs.coresignal.com/
    Search returns a list of member IDs; each ID is then "collected" to get
    the full profile. To keep this demo responsive, we cap the number of
    per-record "collect" calls to `limit`.
    """
    name = "CORESIGNAL"

    def search(self, keywords: List[str], locations: List[str],
               seniority: Optional[str], limit: int = 15) -> List[CandidateResult]:
        if not self.is_configured:
            return self._mock_results(keywords, locations, seniority, limit)

        should = []
        if keywords:
            should += [{"match": {"title": kw}} for kw in keywords]
        if seniority:
            should.append({"match": {"title": seniority}})
        must = []
        if locations:
            must.append({
                "bool": {
                    "should": [{"match": {"location": loc}} for loc in locations],
                    "minimum_should_match": 1,
                }
            })

        es_dsl = {
            "query": {
                "bool": {
                    "must": must,
                    "should": should,
                    "minimum_should_match": 1 if should else 0,
                }
            }
        }

        headers = {"apikey": self.api_key, "Content-Type": "application/json"}

        try:
            search_resp = httpx.post(CORESIGNAL_SEARCH_URL, headers=headers, json=es_dsl, timeout=20.0)
            search_resp.raise_for_status()
            ids = search_resp.json()
            if not isinstance(ids, list):
                ids = ids.get("results", [])
            ids = ids[:limit]

            results = []
            with httpx.Client(headers=headers, timeout=20.0) as client:
                for member_id in ids:
                    try:
                        detail_resp = client.get(CORESIGNAL_COLLECT_URL.format(id=member_id))
                        detail_resp.raise_for_status()
                        profile = detail_resp.json()
                    except Exception:
                        continue
                    experience = (profile.get("experience") or [{}])
                    current = next((e for e in experience if e.get("active_experience")), experience[0] if experience else {})
                    results.append(CandidateResult(
                        external_id=str(profile.get("id") or member_id),
                        full_name=profile.get("full_name") or profile.get("name"),
                        title=current.get("position_title") or profile.get("title"),
                        company=current.get("company_name"),
                        location=profile.get("location_country") or profile.get("location_full"),
                        linkedin_url=profile.get("linkedin_url") or profile.get("professional_network_url"),
                        email=None,
                        phone_number=None,
                        skills=[s.get("skill") if isinstance(s, dict) else s for s in (profile.get("inferred_skills") or [])],
                        raw_profile=profile,
                    ))
            return results or self._mock_results(keywords, locations, seniority, limit)
        except Exception as exc:  # noqa: BLE001
            fallback = self._mock_results(keywords, locations, seniority, limit)
            for r in fallback:
                r["raw_profile"]["provider_error"] = str(exc)
            return fallback
