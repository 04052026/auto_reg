"""Mail.tm - FREE disposable email with REST API. No API key required."""

import time
import random
import string
import json
from typing import Optional, Set

import requests

from email_providers.base import BaseEmailProvider, EmailAccount


class MailTmProvider(BaseEmailProvider):
    """
    Mail.tm - Free disposable email with full REST API.
    Supports creating accounts, reading inbox, getting messages.
    """

    name = "mail_tm"
    API_BASE = "https://api.mail.tm"

    def __init__(self, proxy: Optional[str] = None):
        self._proxy = proxy
        self._session = requests.Session()
        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self._token = ""

    def create_email(self) -> EmailAccount:
        """Create a new Mail.tm email account."""
        # 1. Get available domain
        domain = self._get_domain()
        if not domain:
            raise RuntimeError("Mail.tm: No available domains")

        # 2. Generate random address
        username = self._random_username()
        address = f"{username}@{domain}"
        password = self._random_password()

        # 3. Create account
        resp = self._session.post(
            f"{self.API_BASE}/accounts",
            json={"address": address, "password": password},
            timeout=15,
        )

        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Mail.tm: Failed to create account: {resp.status_code} {resp.text[:200]}")

        data = resp.json()
        account_id = data.get("id", "")

        # 4. Login to get token
        self._login(address, password)

        return EmailAccount(
            email=address,
            account_id=account_id,
            token=self._token,
            extra={"password": password},
        )

    def wait_for_code(
        self,
        account: EmailAccount,
        keyword: str = "",
        timeout: int = 120,
        code_pattern: Optional[str] = None,
    ) -> Optional[str]:
        """Poll inbox for verification code."""
        # Ensure we're authenticated
        if not self._token and account.extra.get("password"):
            self._login(account.email, account.extra["password"])

        deadline = time.time() + timeout
        poll_interval = 5
        seen_ids: Set[str] = set()

        while time.time() < deadline:
            try:
                messages = self._get_messages()
                for msg in messages:
                    msg_id = msg.get("id", "")
                    if msg_id in seen_ids:
                        continue
                    seen_ids.add(msg_id)

                    # Get full message
                    full_msg = self._get_message(msg_id)
                    text = full_msg.get("text", "")
                    html_field = full_msg.get("html", "")
                    # html can be a string or list depending on API version
                    if isinstance(html_field, list):
                        html_field = html_field[0] if html_field else ""
                    text = text or html_field or ""
                    subject = full_msg.get("subject", "")
                    full_text = f"{subject} {text}"

                    if keyword and keyword.lower() not in full_text.lower():
                        continue

                    code = self._extract_code(full_text, code_pattern)
                    if code:
                        return code
            except Exception:
                pass

            time.sleep(poll_interval)

        return None

    def _get_domain(self) -> str:
        """Get first available domain."""
        try:
            resp = self._session.get(f"{self.API_BASE}/domains", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                domains = data.get("hydra:member", data) if isinstance(data, dict) else data
                if domains:
                    return domains[0].get("domain", "")
        except Exception:
            pass
        return ""

    def _login(self, address: str, password: str):
        """Login to get JWT token."""
        resp = self._session.post(
            f"{self.API_BASE}/token",
            json={"address": address, "password": password},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            self._token = data.get("token", "")
            self._session.headers["Authorization"] = f"Bearer {self._token}"

    def _get_messages(self) -> list:
        """Get inbox messages."""
        resp = self._session.get(f"{self.API_BASE}/messages", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("hydra:member", data) if isinstance(data, dict) else data
        return []

    def _get_message(self, message_id: str) -> dict:
        """Get full message content."""
        resp = self._session.get(f"{self.API_BASE}/messages/{message_id}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return {}

    def _random_username(self, length: int = 12) -> str:
        """Generate random username."""
        chars = string.ascii_lowercase + string.digits
        return "kiro" + "".join(random.choices(chars, k=length))

    def _random_password(self, length: int = 16) -> str:
        """Generate random password."""
        chars = string.ascii_letters + string.digits + "!@#$%"
        return "".join(random.choices(chars, k=length))
