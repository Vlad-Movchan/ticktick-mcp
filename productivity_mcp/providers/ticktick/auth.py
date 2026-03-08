import json
import os
import time
from pathlib import Path

import httpx

from productivity_mcp.providers.ticktick.config import get_settings

TICKTICK_AUTH_URL = "https://ticktick.com/oauth/authorize"
TICKTICK_TOKEN_URL = "https://ticktick.com/oauth/token"
TICKTICK_SCOPE = "tasks:read tasks:write"


def get_auth_url() -> str:
    settings = get_settings()
    params = (
        f"?client_id={settings.TICKTICK_CLIENT_ID}"
        f"&response_type=code"
        f"&scope={TICKTICK_SCOPE.replace(' ', '+')}"
        f"&redirect_uri={settings.TICKTICK_REDIRECT_URI}"
    )
    return TICKTICK_AUTH_URL + params


def exchange_code(code: str) -> dict:
    settings = get_settings()
    response = httpx.post(
        TICKTICK_TOKEN_URL,
        auth=(settings.TICKTICK_CLIENT_ID, settings.TICKTICK_CLIENT_SECRET),
        data={
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.TICKTICK_REDIRECT_URI,
        },
    )
    response.raise_for_status()
    tokens = response.json()
    # Store absolute expiry timestamp
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
    return tokens


def _token_path() -> Path:
    custom = os.environ.get("TICKTICK_TOKEN_PATH")
    if custom:
        return Path(custom)
    return Path.home() / ".ticktick-mcp" / "tokens.json"


def load_tokens() -> dict | None:
    path = _token_path()
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_tokens(tokens: dict) -> None:
    path = _token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens, indent=2))
    path.chmod(0o600)


def _refresh_tokens(tokens: dict) -> dict:
    settings = get_settings()
    response = httpx.post(
        TICKTICK_TOKEN_URL,
        auth=(settings.TICKTICK_CLIENT_ID, settings.TICKTICK_CLIENT_SECRET),
        data={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        },
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Token refresh failed ({response.status_code}): {response.text}. "
            "Run the ticktick_authorize tool to re-authenticate."
        )
    new_tokens = response.json()
    new_tokens["expires_at"] = time.time() + new_tokens.get("expires_in", 3600)
    return new_tokens


def get_valid_token() -> str:
    tokens = load_tokens()
    if tokens is None:
        raise RuntimeError(
            "Not authenticated. Run the ticktick_authorize tool to obtain tokens."
        )
    # Refresh if within 60 seconds of expiry
    if time.time() >= tokens.get("expires_at", 0) - 60:
        tokens = _refresh_tokens(tokens)
        save_tokens(tokens)
    return tokens["access_token"]
