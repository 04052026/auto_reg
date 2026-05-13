"""TempMail.lol - FREE temporary email provider. No API key required."""

import time
import json
import re
from typing import Optional, Set

import requests

from email_providers.base import BaseEmailProvider, EmailAccount


class TempMailLolProvider(BaseEmailProvider):
    """
    TempMail.lol - Completely free temporary email service.
    No registration, no API key, no limits.
    """

    name = "tempmail_lol"
    API_BASE = "https://api.tempmail.lol"

    def __init__(self, proxy: Optional[str] = None):
        self._proxy = proxy
        self._session = requests.Session()
        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
            "Accept": "application/json",
        })

    def create_email(self) -> EmailAccount:
        """Generate a new temporary email address."""
        resp = self._session.post(f"{self.API_BASE}/generate", timeout=15)
        resp.raise_for_status()
        data = resp.json()

        address = data.get("address", "")
        token = data.get("token", "")

        if not address:
            raise RuntimeError("TempMail.lol: Failed to generate email address")

        return EmailAccount(
            email=address,
            token=token,
            account_id=token,
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
        poll_interval = 5  # seconds

        while time.time() < deadline:
            try:
                emails = self._fetch_emails(account.token)
                for email_data in emails:
                    body = email_data.get("body", "") or email_data.get("html", "")
                    subject = email_data.get("subject", "")
                    full_text = f"{subject} {body}"

                    # Filter by keyword if specified
                    if keyword and keyword.lower() not in full_text.lower():
                        continue

                    code = self._extract_code(full_text, code_pattern)
                    if code:
                        return code
            except Exception:
                pass

            time.sleep(poll_interval)

        return None

    def _fetch_emails(self, token: str) -> list:
        """Fetch emails from inbox."""
        resp = self._session.get(
            f"{self.API_BASE}/auth/{token}",
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("email", [])
        return []
