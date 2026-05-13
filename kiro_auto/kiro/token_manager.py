"""Token management - refresh and validate Kiro tokens."""

import logging
from typing import Tuple, Optional

import requests

from core.db import get_account, get_latest_account, update_account_tokens

logger = logging.getLogger(__name__)

OIDC_ENDPOINT = "https://oidc.us-east-1.amazonaws.com"


def refresh_token(
    refresh_token_val: str,
    client_id: str,
    client_secret: str,
) -> Tuple[bool, dict]:
    """Refresh a Kiro OIDC token. Returns (success, token_data)."""
    if not refresh_token_val or not client_id or not client_secret:
        return False, {"error": "Missing refreshToken/clientId/clientSecret"}

    try:
        resp = requests.post(
            f"{OIDC_ENDPOINT}/token",
            json={
                "grantType": "refresh_token",
                "clientId": client_id,
                "clientSecret": client_secret,
                "refreshToken": refresh_token_val,
            },
            headers={
                "Content-Type": "application/json",
                "User-Agent": "aws-sdk-rust/1.3.9 os/macOS lang/rust",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return True, {
                "accessToken": data.get("accessToken", ""),
                "refreshToken": data.get("refreshToken", refresh_token_val),
                "expiresIn": data.get("expiresIn", 3600),
            }
        return False, {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return False, {"error": str(e)}


def refresh_account_token(account_id: Optional[int] = None) -> bool:
    """Refresh token for a specific account or the latest one."""
    import json

    if account_id:
        account = get_account(account_id)
    else:
        account = get_latest_account()

    if not account:
        logger.error("No account found to refresh")
        return False

    aid = account["id"]
    try:
        extra = json.loads(account.get("extra_json", "{}"))
    except Exception:
        extra = {}

    rt = account.get("refresh_token", "") or extra.get("refreshToken", "")
    cid = account.get("client_id", "") or extra.get("clientId", "")
    cs = account.get("client_secret", "") or extra.get("clientSecret", "")

    if not rt or not cid or not cs:
        logger.error(f"Account #{aid} missing refresh credentials")
        return False

    ok, result = refresh_token(rt, cid, cs)
    if ok:
        update_account_tokens(aid, result)
        logger.info(f"Token refreshed for account #{aid}")
        return True
    else:
        logger.error(f"Token refresh failed for #{aid}: {result.get('error', '')}")
        return False


def validate_token(access_token: str) -> bool:
    """Check if an access token is still valid."""
    # Simple validation: try to decode JWT and check expiration
    try:
        import base64
        import json as _json
        import time

        parts = access_token.split(".")
        if len(parts) != 3:
            return False

        payload = parts[1]
        # Add padding
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        data = _json.loads(decoded)

        exp = data.get("exp", 0)
        if exp and exp > time.time():
            return True
        return False
    except Exception:
        return False
