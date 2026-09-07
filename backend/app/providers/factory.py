from typing import Dict, Type

from app.config import settings
from app.providers.base import BasePeopleSearchProvider
from app.providers.pdl import PDLProvider
from app.providers.apollo import ApolloProvider
from app.providers.proxycurl import ProxycurlProvider
from app.providers.coresignal import CoresignalProvider

_PROVIDER_CLASSES: Dict[str, Type[BasePeopleSearchProvider]] = {
    "PDL": PDLProvider,
    "APOLLO": ApolloProvider,
    "PROXYCURL": ProxycurlProvider,
    "CORESIGNAL": CoresignalProvider,
}

_API_KEYS = {
    "PDL": lambda: settings.PDL_API_KEY,
    "APOLLO": lambda: settings.APOLLO_API_KEY,
    "PROXYCURL": lambda: settings.PROXYCURL_API_KEY,
    "CORESIGNAL": lambda: settings.CORESIGNAL_API_KEY,
}


def get_provider(name: str) -> BasePeopleSearchProvider:
    name = name.upper()
    if name == "MOCK":
        # Use PDL's mock generator directly without requiring a key
        return PDLProvider(api_key=None)
    if name not in _PROVIDER_CLASSES:
        raise ValueError(f"Unknown provider '{name}'. Valid: {list(_PROVIDER_CLASSES) + ['MOCK']}")
    api_key = _API_KEYS[name]()
    return _PROVIDER_CLASSES[name](api_key=api_key)


def list_providers():
    return [
        {"id": key, "configured": bool(_API_KEYS[key]())}
        for key in _PROVIDER_CLASSES
    ]
