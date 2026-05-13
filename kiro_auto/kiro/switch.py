"""Switch Kiro IDE to use a registered account."""

import os
import json
import hashlib
import tempfile
import logging
from typing import Tuple, Optional
from datetime import datetime, timezone, timedelta

from core.db import get_account, get_latest_account, update_account_tokens

logger = logging.getLogger(__name__)

OIDC_ENDPOINT = "https://oidc.us-east-1.amazonaws.com"
BUILDER_ID_START_URL = "https://view.awsapps.com/start"


def _calculate_client_id_hash(start_url: str) -> str:
    """Calculate clientIdHash matching Kiro IDE source."""
    input_str = json.dumps({"startUrl": start_url}, separators=(",", ":"))
    return hashlib.sha1(input_str.encode()).hexdigest()


def _get_cache_dir() -> str:
    """Get AWS SSO cache directory."""
    home = os.environ.get("USERPROFILE") or os.environ.get("HOME", "")
    return os.path.join(home, ".aws", "sso", "cache")


def _atomic_write(filepath: str, content: str):
    """Write file atomically."""
    dir_path = os.path.dirname(filepath)
    os.makedirs(dir_path, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, filepath)
    except Exception:
        try:
            os.close(fd)
        except Exception:
            pass
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def switch_kiro_account_local(info: dict) -> Tuple[bool, str]:
    """
    Switch Kiro IDE to use the given account tokens.
    Writes to ~/.aws/sso/cache/ which Kiro IDE reads.
    """
    access_token = info.get("accessToken", "")
    refresh_token = info.get("refreshToken", "")
    client_id = info.get("clientId", "")
    client_secret = info.get("clientSecret", "")
    region = info.get("region", "us-east-1")

    if not access_token:
        return False, "No accessToken available"

    cache_dir = _get_cache_dir()
    os.makedirs(cache_dir, exist_ok=True)

    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )

    client_id_hash = _calculate_client_id_hash(BUILDER_ID_START_URL)

    token_data = {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "expiresAt": expires_at,
        "authMethod": "IdC",
        "provider": "BuilderId",
        "clientIdHash": client_id_hash,
        "region": region,
    }

    try:
        token_path = os.path.join(cache_dir, "kiro-auth-token.json")
        _atomic_write(token_path, json.dumps(token_data, indent=2))

        # Write client registration
        if client_id and client_secret:
            client_expires = (
                datetime.now(timezone.utc) + timedelta(days=90)
            ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            client_reg = {
                "clientId": client_id,
                "clientSecret": client_secret,
                "expiresAt": client_expires,
            }
            client_path = os.path.join(cache_dir, f"{client_id_hash}.json")
            _atomic_write(client_path, json.dumps(client_reg, indent=2))

        return True, "Switched successfully"
    except Exception as e:
        return False, f"Switch failed: {e}"


def switch_to_account(account_id: int) -> bool:
    """Switch Kiro IDE to a specific account from DB."""
    account = get_account(account_id)
    if not account:
        logger.error(f"Account #{account_id} not found")
        return False

    # Parse extra_json for tokens
    try:
        extra = json.loads(account.get("extra_json", "{}"))
    except Exception:
        extra = {}

    info = {
        "accessToken": account.get("access_token", "") or extra.get("accessToken", ""),
        "refreshToken": account.get("refresh_token", "") or extra.get("refreshToken", ""),
        "clientId": account.get("client_id", "") or extra.get("clientId", ""),
        "clientSecret": account.get("client_secret", "") or extra.get("clientSecret", ""),
        "region": account.get("region", "us-east-1"),
    }

    # Refresh token if possible
    if info["refreshToken"] and info["clientId"] and info["clientSecret"]:
        try:
            from kiro.token_manager import refresh_token
            ok, new_tokens = refresh_token(
                info["refreshToken"], info["clientId"], info["clientSecret"]
            )
            if ok:
                info["accessToken"] = new_tokens["accessToken"]
                info["refreshToken"] = new_tokens.get("refreshToken", info["refreshToken"])
                # Update DB
                update_account_tokens(account_id, new_tokens)
        except Exception:
            pass

    ok, msg = switch_kiro_account_local(info)
    if ok:
        logger.info(f"Switched to account #{account_id}: {account.get('email', '')}")
    else:
        logger.error(f"Switch failed for #{account_id}: {msg}")
    return ok
