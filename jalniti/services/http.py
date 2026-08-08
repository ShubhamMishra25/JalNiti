"""Shared HTTP client for backend API calls."""
from __future__ import annotations

from typing import Optional

import requests

TIMEOUT = 30
JSON_HEADERS = {"Content-Type": "application/json"}


class BackendClient:
    """Thin wrapper around a requests.Session for Water Wallet backend calls."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.session = requests.Session()

    def get(self, path: str, params: Optional[dict] = None, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", TIMEOUT)
        return self.session.get(f"{self.base_url}{path}", params=params, **kwargs)

    def post(self, path: str, data: Optional[dict] = None, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", TIMEOUT)
        headers = kwargs.get("headers") or {}
        headers = {**JSON_HEADERS, **headers}
        return self.session.post(f"{self.base_url}{path}", json=data, headers=headers, **kwargs)