"""
Kiro / AWS Builder ID Registration - Playwright-based.
Adapted from platforms/kiro/core.py for standalone use.
"""

import time
import json
import random
import hashlib
import logging
import re
import threading
from typing import Tuple, Optional, Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import requests
from playwright.sync_api import sync_playwright, Page, Locator

from kiro.fingerprint import build_random_profile

logger = logging.getLogger(__name__)

KIRO_SIGNIN_URL = "https://app.kiro.dev/signin"
KIRO_IDC_REGION = "us-east-1"
KIRO_IDC_START_URL = "https://view.awsapps.com/start"
KIRO_IDC_SCOPES = [
    "codewhisperer:completions",
    "codewhisperer:analysis",
    "codewhisperer:conversations",
    "codewhisperer:transformations",
    "codewhisperer:taskassist",
]



def _generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    import string
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*"),
    ]
    pwd += random.choices(chars, k=length - 4)
    random.shuffle(pwd)
    return "".join(pwd)


class _DesktopAuthCallbackServer:
    """Local HTTP server for OAuth callback."""

    def __init__(self, expected_state: str):
        self.expected_state = expected_state
        self.result = None
        self.error = None
        self._event = threading.Event()
        self._server = None
        self._thread = None

    def start(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path != "/oauth/callback":
                    self.send_response(404)
                    self.end_headers()
                    return
                params = parse_qs(parsed.query)
                error = params.get("error", [None])[0]
                state = params.get("state", [None])[0]
                code = params.get("code", [None])[0]

                if error:
                    outer.error = params.get("error_description", [error])[0]
                elif state != outer.expected_state:
                    outer.error = "State mismatch"
                elif not code:
                    outer.error = "Missing code"
                else:
                    outer.result = {"code": code, "state": state}

                outer._event.set()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h3>Auth complete. Close this tab.</h3>")

            def log_message(self, *args):
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def redirect_uri(self) -> str:
        port = self._server.server_address[1]
        return f"http://127.0.0.1:{port}/oauth/callback"

    def wait(self, timeout: int = 120):
        if not self._event.wait(timeout):
            raise TimeoutError("OAuth callback timeout")
        if self.error:
            raise RuntimeError(self.error)
        return self.result

    def close(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()


class KiroRegister:
    """Handles Kiro account registration via Playwright."""

    def __init__(self, proxy: Optional[str] = None, headless: bool = True):
        self.proxy = proxy
        self.headless = headless
        self.log_fn: Callable = lambda msg: logger.info(msg)
        self._captured_tokens = {}
        self._pw = None
        self._browser = None
        self._context = None

    def log(self, msg: str):
        self.log_fn(f"[KIRO] {msg}")

    def register(
        self,
        email: str,
        pwd: Optional[str] = None,
        name: str = "Kiro User",
        otp_callback: Optional[Callable] = None,
        otp_timeout: int = 120,
    ) -> Tuple[bool, dict]:
        """
        Full registration flow. Returns (success, info_dict).
        info_dict contains: email, password, accessToken, refreshToken, etc.
        """
        password = pwd or _generate_password()
        display_name = self._randomize_name(name)

        try:
            self._init_browser()
            page = self._context.new_page()

            # Navigate to Kiro sign-in
            self.log(f"Navigating to {KIRO_SIGNIN_URL}")
            page.goto(KIRO_SIGNIN_URL, wait_until="domcontentloaded", timeout=30000)
            self._human_sleep(2, 4)
            self._accept_cookie_banner(page)

            # Click "Builder ID" or "AWS Builder ID" button to redirect to AWS SSO
            self.log("Looking for Builder ID login button...")
            if page.locator('button:has-text("Builder ID")').count() > 0:
                page.click('button:has-text("Builder ID")')
                self.log("Clicked 'Builder ID' button")
            elif page.locator('text="AWS Builder ID"').count() > 0:
                page.locator('text="AWS Builder ID"').first.click()
                self.log("Clicked 'AWS Builder ID' link")
            elif page.locator('a:has-text("Builder ID")').count() > 0:
                page.locator('a:has-text("Builder ID")').first.click()
                self.log("Clicked Builder ID link")
            else:
                # Maybe page auto-redirects or has different layout
                self.log("No Builder ID button found, checking if already on AWS SSO...")

            # Wait for redirect to AWS sign-in page
            self.log("Waiting for AWS SSO page...")
            try:
                page.wait_for_url(re.compile(r"signin\.aws|authorize\.id\.aws|id\.awsapps"), timeout=30000)
            except Exception:
                # Maybe already on the right page
                self.log(f"Current URL: {page.url}")
                if "signin.aws" not in page.url and "authorize" not in page.url:
                    return False, {"error": f"Failed to redirect to AWS SSO. Current URL: {page.url}"}

            self._human_sleep(1, 2)
            self._accept_cookie_banner(page)

            # Enter email on AWS SSO page
            self.log(f"Entering email: {email}")
            self._enter_email(page, email)
            self._human_sleep(1, 2)

            # Wait for next step (OTP or Name)
            step, locator, error = self._wait_for_post_email_step(page)

            if step == "error":
                return False, {"error": error}
            elif step == "timeout":
                return False, {"error": "Timeout waiting for next step after email"}

            # Handle Name step if it appears first
            if step == "name":
                self.log(f"Entering name: {display_name}")
                self._type_human(page, locator, display_name)
                self._click_primary(page)
                self._human_sleep(1, 2)
                # Now wait for OTP
                ok, error, locator = self._wait_for_otp_step(page)
                if not ok:
                    return False, {"error": error or "OTP step not found"}

            # OTP step
            if otp_callback:
                self.log("Waiting for OTP from email...")
                code = otp_callback()
                if not code:
                    return False, {"error": "Failed to get verification code"}
                self.log(f"Entering OTP: {code}")
                self._type_human(page, locator, code)
                self._click_primary(page)
                self._human_sleep(1, 2)
            else:
                return False, {"error": "No OTP callback provided"}

            # Wait for password step or name step
            self._human_sleep(1, 2)
            current_url = page.url

            # Check if we need to enter name after OTP
            name_field = self._find_name_input(page)
            if name_field:
                self.log(f"Entering name: {display_name}")
                self._type_human(page, name_field, display_name)
                self._click_primary(page)
                self._human_sleep(1, 2)

            # Password step
            ok, error = self._wait_for_password_step(page)
            if ok:
                self.log("Setting password...")
                self._fill_passwords(page, password)
                self._click_primary(page)
                self._human_sleep(2, 4)

            # Wait for successful login
            self.log("Waiting for registration to complete...")
            self._wait_for_completion(page)
            self._capture_tokens(page)

            # Try desktop token flow
            desktop_tokens = {}
            try:
                desktop_tokens = self._get_desktop_tokens(email, password, otp_callback)
            except Exception as e:
                self.log(f"Desktop token capture skipped: {e}")

            # Merge all tokens
            info = {
                "email": email,
                "password": password,
                "name": display_name,
                "region": KIRO_IDC_REGION,
                **self._captured_tokens,
                **desktop_tokens,
            }

            self.log(f"Registration successful: {email}")
            return True, info

        except Exception as e:
            self.log(f"Registration error: {e}")
            return False, {"error": str(e)}
        finally:
            self._close_browser()

    # === Browser helpers ===

    def _init_browser(self):
        self._pw = sync_playwright().start()
        launch_opts = {
            "headless": self.headless,
            "args": ["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        }
        if self.proxy:
            launch_opts["proxy"] = {"server": self.proxy}

        self._browser = self._pw.chromium.launch(**launch_opts)
        profile = build_random_profile()

        self.log(f"Profile: {profile['name']} / {profile['locale']} / {profile['timezone_id']}")

        self._context = self._browser.new_context(
            user_agent=profile["user_agent"],
            locale=profile["locale"],
            timezone_id=profile["timezone_id"],
            viewport=profile["viewport"],
            color_scheme=profile["color_scheme"],
            reduced_motion=profile["reduced_motion"],
        )
        self._context.set_extra_http_headers({"Accept-Language": f"{profile['locale']},en;q=0.9"})
        self._context.on("response", self._on_response)

    def _close_browser(self):
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass

    def _human_sleep(self, min_s: float = 0.2, max_s: float = 0.6):
        time.sleep(random.uniform(min_s, max_s))

    def _randomize_name(self, base: str) -> str:
        suffix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=3))
        suffix += str(random.randint(10, 99))
        return f"{base.strip()} {suffix}"

    def _accept_cookie_banner(self, page: Page):
        try:
            for sel in ['button:has-text("Accept")', 'button[id*="awsccc-accept"]']:
                btn = page.locator(sel).first
                if btn.count() > 0 and btn.is_visible():
                    btn.click(timeout=2000)
                    self._human_sleep(0.3, 0.6)
                    return
        except Exception:
            pass

    def _enter_email(self, page: Page, email: str):
        # AWS SSO uses dynamic IDs but consistent placeholder
        selectors = [
            'input[placeholder="username@example.com"]',
            'input[type="email"]',
            'input[name="email"]',
            'input[autocomplete="username"]',
        ]
        # Wait for any email input to appear (AWS SSO can be slow)
        for sel in selectors:
            try:
                el = page.locator(sel).first
                el.wait_for(state="visible", timeout=15000)
                self._type_human(page, el, email)
                self._click_primary(page)
                return
            except Exception:
                continue

        # Fallback: find any visible text input
        try:
            all_inputs = page.locator('input[type="text"], input:not([type])').all()
            for inp in all_inputs:
                if inp.is_visible():
                    self.log("Using fallback: first visible text input")
                    self._type_human(page, inp, email)
                    self._click_primary(page)
                    return
        except Exception:
            pass

        # Debug: log what's on the page
        try:
            self.log(f"Current URL: {page.url}")
            inputs = page.locator("input").all()
            for i, inp in enumerate(inputs):
                self.log(f"  input[{i}]: type={inp.get_attribute('type')} placeholder={inp.get_attribute('placeholder')} id={inp.get_attribute('id')}")
        except Exception:
            pass

        raise RuntimeError("Email input not found on AWS SSO page")

    def _type_human(self, page: Page, locator, text: str):
        el = locator.first if hasattr(locator, 'first') else locator
        el.click(delay=random.randint(45, 160))
        try:
            el.clear()
        except Exception:
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
        for char in text:
            page.keyboard.type(char, delay=random.randint(50, 200))
            if random.random() < 0.1:
                self._human_sleep(0.05, 0.2)
        self._human_sleep(0.2, 0.5)

    def _click_primary(self, page: Page):
        self._human_sleep(0.4, 0.9)
        selectors = [
            'button[data-testid*="verify-button"]',
            'button[data-testid*="next-button"]',
            'button[type="submit"]:has-text("Continue")',
            'button[type="submit"]:has-text("Verify")',
            'button[type="submit"]:has-text("Create")',
            'button[type="submit"]:has-text("Next")',
            'button[type="submit"]:visible',
        ]
        for sel in selectors:
            try:
                btn = page.locator(sel).first
                if btn.count() > 0 and btn.is_visible():
                    btn.click(timeout=2000)
                    return
            except Exception:
                continue

    def _wait_for_post_email_step(self, page: Page, timeout_ms: int = 30000):
        deadline = time.time() + (timeout_ms / 1000)
        while time.time() < deadline:
            # Check for OTP
            otp = self._find_otp_input(page)
            if otp:
                return "otp", otp, ""
            # Check for name
            name = self._find_name_input(page)
            if name:
                return "name", name, ""
            # Check for error
            error = self._get_alert_text(page)
            if error:
                return "error", None, error
            self._human_sleep(0.3, 0.6)
        return "timeout", None, "Timeout"

    def _wait_for_otp_step(self, page: Page, timeout_ms: int = 30000):
        deadline = time.time() + (timeout_ms / 1000)
        while time.time() < deadline:
            field = self._find_otp_input(page)
            if field:
                return True, "", field
            error = self._get_alert_text(page)
            if error:
                return False, error, None
            self._human_sleep(0.3, 0.6)
        return False, "OTP input timeout", None

    def _wait_for_password_step(self, page: Page, timeout_ms: int = 15000):
        deadline = time.time() + (timeout_ms / 1000)
        while time.time() < deadline:
            pwd_input = page.locator('input[type="password"]')
            if pwd_input.count() > 0 and pwd_input.first.is_visible():
                return True, ""
            self._human_sleep(0.3, 0.6)
        return False, "Password step timeout"

    def _fill_passwords(self, page: Page, password: str):
        pwd_field = page.get_by_label("Password", exact=True).first
        confirm_field = page.get_by_label("Confirm password", exact=True).first
        pwd_field.wait_for(state="visible", timeout=10000)
        for field in (pwd_field, confirm_field):
            field.click()
            field.fill(password)
            if field.input_value() != password:
                field.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                field.fill(password)

    def _find_otp_input(self, page: Page):
        candidates = [
            page.get_by_label("Verification code", exact=True),
            page.locator('input[placeholder*="6-digit" i]'),
            page.locator('input[name="code"], input[id*="code"]'),
        ]
        for loc in candidates:
            try:
                if loc.count() > 0 and loc.first.is_visible():
                    return loc.first
            except Exception:
                continue
        return None

    def _find_name_input(self, page: Page):
        candidates = [
            page.get_by_label("Name", exact=True),
            page.locator('input[placeholder="Maria José Silva"]'),
            page.locator('input[autocomplete="name"]'),
            page.locator('input[name="name"]'),
        ]
        for loc in candidates:
            try:
                if loc.count() > 0 and loc.first.is_visible():
                    return loc.first
            except Exception:
                continue
        return None

    def _get_alert_text(self, page: Page) -> str:
        for sel in [".awsui-alert-content", '[role="alert"]']:
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    text = (el.text_content() or "").strip()
                    if text:
                        return text
            except Exception:
                continue
        return ""

    def _wait_for_completion(self, page: Page, timeout: int = 30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            url = page.url
            if "app.kiro.dev" in url and "signin" not in url:
                self._human_sleep(2, 3)
                return
            self._human_sleep(0.5, 1)

    def _on_response(self, response):
        try:
            url = response.url
            if not any(k in url.lower() for k in ["token", "oauth", "auth", "kiro"]):
                return
            if response.status not in range(200, 300):
                return
            body = response.json()
            if isinstance(body, dict):
                tokens = self._extract_tokens(body)
                if tokens:
                    self._captured_tokens.update(tokens)
        except Exception:
            pass

    def _capture_tokens(self, page: Page):
        # From cookies
        try:
            cookies = {c["name"]: c["value"] for c in self._context.cookies()
                      if "kiro.dev" in c.get("domain", "")}
            if cookies.get("AccessToken"):
                self._captured_tokens["webAccessToken"] = cookies["AccessToken"]
            if cookies.get("SessionToken"):
                self._captured_tokens["sessionToken"] = cookies["SessionToken"]
        except Exception:
            pass
        # From localStorage
        try:
            ls = page.evaluate("() => JSON.stringify(window.localStorage)")
            tokens = self._extract_tokens(json.loads(ls))
            self._captured_tokens.update(tokens)
        except Exception:
            pass

    def _extract_tokens(self, data) -> dict:
        found = {}
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                return found
        if isinstance(data, dict):
            wanted = {"accessToken", "refreshToken", "clientId", "clientSecret", "sessionToken"}
            for k, v in data.items():
                if k in wanted and isinstance(v, str) and v:
                    found[k] = v
                elif isinstance(v, (dict, list)):
                    found.update(self._extract_tokens(v))
        elif isinstance(data, list):
            for item in data:
                found.update(self._extract_tokens(item))
        return found

    def _get_desktop_tokens(
        self, email: str, password: str, otp_callback: Optional[Callable]
    ) -> dict:
        """Register OIDC client and get desktop tokens."""
        region = KIRO_IDC_REGION

        # Register client
        resp = requests.post(
            f"https://oidc.{region}.amazonaws.com/client/register",
            json={
                "clientName": "Kiro IDE",
                "clientType": "public",
                "scopes": KIRO_IDC_SCOPES,
                "grantTypes": ["authorization_code", "refresh_token"],
                "redirectUris": ["http://127.0.0.1/oauth/callback"],
                "issuerUrl": KIRO_IDC_START_URL,
            },
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"OIDC client registration failed: {resp.status_code}")

        client_data = resp.json()
        client_id = client_data.get("clientId", "")
        client_secret = client_data.get("clientSecret", "")

        if not client_id or not client_secret:
            raise RuntimeError("OIDC client registration returned empty credentials")

        client_id_hash = hashlib.sha1(
            json.dumps({"startUrl": KIRO_IDC_START_URL}, separators=(",", ":")).encode()
        ).hexdigest()

        return {
            "clientId": client_id,
            "clientSecret": client_secret,
            "clientIdHash": client_id_hash,
        }
