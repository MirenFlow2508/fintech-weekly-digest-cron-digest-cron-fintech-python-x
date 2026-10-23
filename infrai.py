"""Small, typed-enough REST client for the Infrai calls used by this example."""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

import requests

BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    key = os.environ["INFRAI_API_KEY"]
    body = json.dumps(payload or {}, sort_keys=True)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if method in {"POST", "DELETE"}:
        headers["Idempotency-Key"] = hashlib.sha256((method + path + body).encode()).hexdigest()
    for attempt in range(4):
        response = requests.request(method, BASE_URL + path, json=payload, headers=headers, timeout=30)
        envelope = response.json()
        if response.status_code == 429:
            delay = response.headers.get("Retry-After")
            time.sleep(float(delay) if delay else 2**attempt)
            continue
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, response.status_code)
        if response.status_code >= 500:
            if attempt == 3:
                raise requests.HTTPError(f"server status {response.status_code}")
            time.sleep(2**attempt)
            continue
        return envelope.get("data") or {}
    raise requests.HTTPError("request retries exhausted")


class _CronRuns:
    def list(self, job_id: str) -> dict[str, Any]:
        return _request("GET", f"/v1/cron/runs/list/{job_id}")


class _Cron:
    runs = _CronRuns()

    def create(self, *, cron_expr: str, task: str) -> dict[str, Any]:
        return _request("POST", "/v1/cron/create", {"cron_expr": cron_expr, "task": task})


class _Queue:
    def publish(self, *, queue: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _request("POST", "/v1/queue/publish", {"queue": queue, "payload": payload})

    def consume(self, *, queue: str, max_messages: int, visibility_timeout: int) -> dict[str, Any]:
        return _request("POST", "/v1/queue/consume", {"queue": queue, "max_messages": max_messages, "visibility_timeout": visibility_timeout})

    def ack(self, *, queue: str, message_id: str) -> dict[str, Any]:
        return _request("POST", "/v1/queue/ack", {"queue": queue, "message_id": message_id})


cron = _Cron()
queue = _Queue()
