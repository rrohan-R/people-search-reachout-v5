"""
Thin client for the Hunar Voice Agents external API.
Docs: https://api.voice.hunar.ai/docs/external/
"""
import logging
import time
import uuid as _uuid
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings

logger = logging.getLogger("app.hunar")


def _redact(headers: Dict[str, str]) -> Dict[str, str]:
    """Never log the raw API key — show only enough of it to confirm one is set."""
    safe = dict(headers)
    key = safe.get("X-API-Key") or ""
    safe["X-API-Key"] = f"***{key[-4:]}" if len(key) > 4 else ("<empty>" if not key else "***")
    return safe


class HunarAPIError(Exception):
    def __init__(self, status_code: int, message: str, details: Optional[list] = None):
        self.status_code = status_code
        self.message = message
        self.details = details or []
        super().__init__(f"Hunar API error {status_code}: {message}")


class HunarClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.HUNAR_API_KEY
        self.base_url = (base_url or settings.HUNAR_BASE_URL).rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key or "", "Content-Type": "application/json"}

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        call_tag = _uuid.uuid4().hex[:8]  # correlates the request/response pair in the logs

        if not self.is_configured:
            logger.warning(
                "[hunar:%s] %s %s called with NO API KEY configured (HUNAR_API_KEY is unset) — "
                "this request will be rejected by Hunar with 401.",
                call_tag, method, url,
            )

        logger.info(
            "[hunar:%s] -> %s %s headers=%s params=%s json=%s",
            call_tag, method, url, _redact(self._headers()),
            kwargs.get("params"), kwargs.get("json"),
        )

        started = time.monotonic()
        try:
            resp = httpx.request(method, url, headers=self._headers(), timeout=30.0, **kwargs)
        except httpx.RequestError as exc:
            elapsed_ms = round((time.monotonic() - started) * 1000)
            logger.error(
                "[hunar:%s] <- network error after %sms calling %s %s: %s",
                call_tag, elapsed_ms, method, url, exc,
            )
            raise HunarAPIError(0, f"Could not reach Hunar API: {exc}") from exc

        elapsed_ms = round((time.monotonic() - started) * 1000)

        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:
                body = {"message": resp.text}
            logger.error(
                "[hunar:%s] <- %s %s FAILED status=%s (%sms) message=%r details=%s",
                call_tag, method, url, resp.status_code, elapsed_ms,
                body.get("message", "Unknown error"), body.get("details"),
            )
            raise HunarAPIError(resp.status_code, body.get("message", "Unknown error"), body.get("details"))

        logger.info(
            "[hunar:%s] <- %s %s OK status=%s (%sms)",
            call_tag, method, url, resp.status_code, elapsed_ms,
        )
        return resp.json()

    # ---- Agents ----

    def list_agents(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        return self._request("GET", "/agents/", params={"page": page, "page_size": page_size})

    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/agents/{agent_id}/")

    def create_agent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new agent on the Hunar side. `payload` should contain the
        fields documented for POST /agents/ (name, language, voice_persona,
        persona_name, agent_prompt, objective, introduction, result_prompt,
        result_schema, and optionally silence_response / conclusion).
        The response includes the provider-assigned `id`, which the caller
        is responsible for storing locally — there is no separate "agent id"
        the user needs to type in.
        """
        return self._request("POST", "/agents/", json=payload)

    def update_agent(self, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PUT", f"/agents/{agent_id}/", json=payload)

    # ---- Calls ----

    def create_call(
        self,
        agent_id: str,
        callee_name: str,
        mobile_number: str,
        custom_data: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        from_phone_number: Optional[str] = None,
        guardrails: Optional[Dict[str, Any]] = None,
        timezone: Optional[str] = None,
        retry_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "agent_id": agent_id,
            "callee_name": callee_name,
            "mobile_number": mobile_number,
            "custom_data": custom_data or {},
        }
        if request_id:
            payload["request_id"] = request_id
        if from_phone_number:
            payload["from_phone_number"] = from_phone_number
        # guardrails/timezone are how a "scheduled" call is expressed to
        # Hunar: the call is created now, but Hunar itself only actually
        # dials once the current time falls inside the window. Omitting
        # guardrails (the "call now" path in outreach.py) uses the org
        # default / dials immediately instead.
        if guardrails:
            payload["guardrails"] = guardrails
        if timezone:
            payload["timezone"] = timezone
        if retry_config:
            payload["retry_config"] = retry_config
        return self._request("POST", "/calls/", json=payload)

    def create_bulk_calls(
        self,
        agent_id: str,
        data: List[Dict[str, Any]],
        request_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {"agent_id": agent_id, "data": data}
        if request_id:
            payload["request_id"] = request_id
        return self._request("POST", "/calls/bulk/", json=payload)

    def get_call(self, call_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/calls/{call_id}/")

    def list_calls(self, page: int = 1, page_size: int = 20, **filters) -> Dict[str, Any]:
        params = {"page": page, "page_size": page_size, **filters}
        return self._request("GET", "/calls/", params=params)

    # ---- Numbers ----

    def list_numbers(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        return self._request("GET", "/numbers/", params={"page": page, "page_size": page_size})
