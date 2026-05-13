"""1secMail - FREE disposable email with fast delivery. No API key required.

Domains: 1secmail.com, 1secmail.org, 1secmail.net, bheps.com, dcctb.com, etc.
These domains are well-known and generally accepted by major services including AWS.
API: https://www.1secmail.com/api/v1/
"""

import time
import random
import string
from typing import Optional, Set

import requests

from email_providers.base import BaseEmailProvider, EmailAccount


class OneSecMailProvider(BaseEmailProvider):
    """
    1secMail - Fast free disposable email.
    Uses multiple domains that are widely accepted.
    No registration, no API key required.
    """

    name = "onesecmail"
    API_BASE = "https://www.1secmail.com/api/v1/"

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
        """Generate a random email on 1secmail domains."""
        # Method 1: Use their random generation endpoint
        try:
            resp = self._session.get(
                self.API_BASE,
                params={"action": "genRandomMailbox", "count": 1},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and data[0]:
                    address = data[0]
                    login, domain = address.split("@")
                    return EmailAccount(
                        email=address,
                        account_id=login,
                        extra={"login": login, "domain": domain},
                    )
        except Exception:
            pass

        # Method 2: Generate manually with known domains
        domains = self._get_domains()
        if not domains:
            domains = ["1secmail.com", "1secmail.org", "1secmail.net"]

        domain = random.choice(domains)
        login = self._random_login()
        address = f"{login}@{domain}"

        return EmailAccount(
            email=address,
            account_id=login,
            extra={"login": login, "domain": domain},
        )

    def wait_for_code(
        self,
        account: EmailAccount,
        keyword: str = "",
        timeout: int = 120,
        code_pattern: Optional[str] = None,
    ) -> Optional[str]:
        """Poll inbox for verification code."""
        login = account.extra.get("login", "")
        domain = account.extra.get("domain", "")

        if not login or not domain:
            # Parse from email
            parts = account.email.split("@")
            if len(parts) == 2:
                login, domain = parts
            else:
                return None

        deadline = time.time() + timeout
        poll_interval = 3  # 1secmail is fast, poll every 3s
        seen_ids: Set[int] = set()

        while time.time() < deadline:
            try:
                messages = self._get_messages(login, domain)
                for msg in messages:
                    msg_id = msg.get("id", 0)
                    if msg_id in seen_ids:
                        continue
                    seen_ids.add(msg_id)

                    # Check subject first (fast filter)
                    subject = msg.get("subject", "")
                    if keyword and keyword.lower() not in subject.lower():
                        # Still fetch body to check
                        pass

                    # Get full message body
                    full_msg = self._read_message(login, domain, msg_id)
                    body = full_msg.get("body", "") or full_msg.get("textBody", "")
                    html_body = full_msg.get("htmlBody", "")
                    full_text = f"{subject} {body} {html_body}"

                    if keyword and keyword.lower() not in full_text.lower():
                        continue

                    code = self._extract_code(full_text, code_pattern)
                    if code:
                        return code
            except Exception:
                pass

            time.sleep(poll_interval)

        return None

    def _get_domains(self) -> list:
        """Get list of available domains."""
        try:
            resp = self._session.get(
                self.API_BASE,
                params={"action": "getDomainList"},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []

    def _get_messages(self, login: str, domain: str) -> list:
        """Get inbox messages."""
        resp = self._session.get(
            self.API_BASE,
            params={
                "action": "getMessages",
                "login": login,
                "domain": domain,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return []

    def _read_message(self, login: str, domain: str, msg_id: int) -> dict:
        """Read a specific message."""
        resp = self._session.get(
            self.API_BASE,
            params={
                "action": "readMessage",
                "login": login,
                "domain": domain,
                "id": msg_id,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return {}

    def _random_login(self, length: int = 12) -> str:
        """Generate random login name."""
        chars = string.ascii_lowercase + string.digits
        return "kiro" + "".join(random.choices(chars, k=length))
