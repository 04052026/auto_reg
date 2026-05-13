"""Cloudflare Worker Email - Self-hosted FREE email receiver."""

import time
import random
import string
from typing import Optional, Set

import requests

from email_providers.base import BaseEmailProvider, EmailAccount


class CfWorkerProvider(BaseEmailProvider):
    """
    Cloudflare Worker Email - Self-hosted on Cloudflare free tier.
    Based on cloudflare_temp_email project.
    Requires deploying a Cloudflare Worker (free) with a custom domain.
    """

    name = "cfworker"

    def __init__(
        self,
        api_url: str = "",
        domain: str = "",
        proxy: Optional[str] = None,
    ):
        self._api_url = api_url.rstrip("/") if api_url else ""
        self._domain = domain
        self._proxy = proxy
        self._session = requests.Session()
        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
            "Accept": "application/json",
        })

    def create_email(self) -> EmailAccount:
        """Generate a random email on the CF Worker domain."""
        if not self._api_url or not self._domain:
            raise RuntimeError(
                "CfWorker: api_url and domain must be configured in config.yaml"
            )

        username = self._random_username()
        address = f"{username}@{self._domain}"

        return EmailAccount(
            email=address,
            account_id=username,
        )

    def wait_for_code(
        self,
        account: EmailAccount,
        keyword: str = "",
        timeout: int = 120,
        code_pattern: Optional[str] = None,
    ) -> Optional[str]:
        """Poll CF Worker inbox for verification code."""
        if not self._api_url:
            return None

        deadline = time.time() + timeout
        poll_interval = 5
        seen_ids: Set[str] = set()

        while time.time() < deadline:
            try:
                emails = self._get_emails(account.email)
                for email_data in emails:
                    mail_id = str(email_data.get("id", ""))
                    if mail_id in seen_ids:
                        continue
                    seen_ids.add(mail_id)

                    subject = email_data.get("subject", "")
                    body = email_data.get("text", "") or email_data.get("html", "")
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

    def _get_emails(self, address: str) -> list:
        """Fetch emails from CF Worker API."""
        try:
            resp = self._session.get(
                f"{self._api_url}/api/mails",
                params={"address": address},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
                return data.get("results", data.get("mails", []))
        except Exception:
            pass
        return []

    def _random_username(self, length: int = 12) -> str:
        """Generate random username."""
        chars = string.ascii_lowercase + string.digits
        return "kiro" + "".join(random.choices(chars, k=length))
