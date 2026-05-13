"""Guerrilla Mail - FREE disposable email. No API key required."""

import time
import random
from typing import Optional, Set

import requests

from email_providers.base import BaseEmailProvider, EmailAccount


class GuerrillaProvider(BaseEmailProvider):
    """
    Guerrilla Mail - Free disposable email.
    Uses their public API without authentication.
    """

    name = "guerrilla"
    API_BASE = "https://api.guerrillamail.com/ajax.php"

    def __init__(self, proxy: Optional[str] = None):
        self._proxy = proxy
        self._session = requests.Session()
        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
        })
        self._sid_token = ""

    def create_email(self) -> EmailAccount:
        """Get a new Guerrilla Mail address."""
        resp = self._session.get(
            self.API_BASE,
            params={"f": "get_email_address", "lang": "en"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        address = data.get("email_addr", "")
        self._sid_token = data.get("sid_token", "")

        if not address:
            raise RuntimeError("Guerrilla Mail: Failed to get email address")

        return EmailAccount(
            email=address,
            account_id=self._sid_token,
            token=self._sid_token,
        )

    def wait_for_code(
        self,
        account: EmailAccount,
        keyword: str = "",
        timeout: int = 120,
        code_pattern: Optional[str] = None,
    ) -> Optional[str]:
        """Poll inbox for verification code."""
        deadline = time.time() + timeout
        poll_interval = 5
        seen_ids: Set[str] = set()

        while time.time() < deadline:
            try:
                emails = self._check_email(account.token)
                for email_data in emails:
                    mail_id = str(email_data.get("mail_id", ""))
                    if mail_id in seen_ids:
                        continue
                    seen_ids.add(mail_id)

                    subject = email_data.get("mail_subject", "")
                    body = email_data.get("mail_body", "")
                    # Try to fetch full email if body is truncated
                    if not body and mail_id:
                        full = self._fetch_email(mail_id, account.token)
                        body = full.get("mail_body", "")

                    full_text = f"{subject} {body}"

                    if keyword and keyword.lower() not in full_text.lower():
                        continue

                    code = self._extract_code(full_text, code_pattern)
                    if code:
                        return code
            except Exception:
                pass

            time.sleep(poll_interval)

        return None

    def _check_email(self, sid_token: str) -> list:
        """Check inbox for new emails."""
        resp = self._session.get(
            self.API_BASE,
            params={
                "f": "check_email",
                "sid_token": sid_token,
                "seq": "0",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("list", [])
        return []

    def _fetch_email(self, mail_id: str, sid_token: str) -> dict:
        """Fetch full email content."""
        resp = self._session.get(
            self.API_BASE,
            params={
                "f": "fetch_email",
                "sid_token": sid_token,
                "email_id": mail_id,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        return {}
