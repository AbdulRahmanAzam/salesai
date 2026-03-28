from __future__ import annotations

from typing import Any

import requests


class HttpClient:
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "prospecting-agent/1.0",
                "Accept": "application/json",
            }
        )

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        resp = self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json()

    def post(
        self,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        resp = self.session.post(
            url,
            json=json_body,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json()
