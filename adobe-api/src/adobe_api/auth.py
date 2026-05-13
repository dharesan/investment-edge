from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


IMS_TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token/v3"


@dataclass(frozen=True)
class AdobeCredentials:
    org_id: str
    client_id: str
    client_secret: str
    scopes: tuple[str, ...]
    technical_account_id: str | None = None
    technical_account_email: str | None = None


def load_credentials(credentials_path: str | Path) -> AdobeCredentials:
    path = Path(credentials_path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    return AdobeCredentials(
        org_id=payload["ORG_ID"],
        client_id=payload["CLIENT_ID"],
        client_secret=payload["CLIENT_SECRETS"][0],
        scopes=tuple(payload.get("SCOPES", [])),
        technical_account_id=payload.get("TECHNICAL_ACCOUNT_ID"),
        technical_account_email=payload.get("TECHNICAL_ACCOUNT_EMAIL"),
    )


def fetch_access_token(credentials: AdobeCredentials, timeout: int = 30) -> str:
    scope = ",".join(credentials.scopes)
    response = requests.post(
        IMS_TOKEN_URL,
        data={
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "grant_type": "client_credentials",
            "scope": scope,
        },
        timeout=timeout,
    )
    response.raise_for_status()

    token_payload: dict[str, Any] = response.json()
    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError("Adobe IMS did not return an access token.")

    return access_token