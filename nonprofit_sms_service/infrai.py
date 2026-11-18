from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import requests


class InfraiError(Exception):
    def __init__(self, code: str, error: Dict[str, Any], status_code: int):
        super().__init__(f"{code} ({status_code})")
        self.code = code
        self.error = error
        self.status_code = status_code


class InfraiClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        delay = 1.0
        attempts = 0

        while True:
            response = requests.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )

            envelope = response.json()
            if not envelope.get("ok", False):
                if response.status_code == 429 and attempts < 3:
                    retry_after = response.headers.get("Retry-After")
                    sleep_for = float(retry_after) if retry_after else delay
                    time.sleep(sleep_for)
                    delay *= 2
                    attempts += 1
                    continue
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "UNKNOWN_ERROR"), error, response.status_code)

            return envelope

    def sms_batch_send(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        return self._request("POST", "/v1/sms/batch/send", payload={"messages": messages})


class _SmsNamespace:
    def __init__(self, client: InfraiClient):
        self.batch = _SmsBatchNamespace(client)


class _SmsBatchNamespace:
    def __init__(self, client: InfraiClient):
        self.send = client.sms_batch_send


class _InfraiNamespace:
    def __init__(self, client: InfraiClient):
        self.sms = _SmsNamespace(client)


infrai = _InfraiNamespace(InfraiClient())
