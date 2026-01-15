# src/utils/secrets.py
from __future__ import annotations
import json
from typing import Any
from google.cloud import secretmanager

_client: secretmanager.SecretManagerServiceClient | None = None

def _client_once() -> secretmanager.SecretManagerServiceClient:
    global _client
    if _client is None:
        _client = secretmanager.SecretManagerServiceClient()
    return _client

def get_secret(name: str, project_id: str) -> Any:
    """
    Fetch a secret (JSON or string) from GCP Secret Manager.
    Assumes default creds (VM SA) can access it.
    """
    sm = _client_once()
    path = f"projects/{project_id}/secrets/{name}/versions/latest"
    resp = sm.access_secret_version(request={"name": path})
    raw = resp.payload.data.decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw