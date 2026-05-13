"""Task execution engine - runs registration tasks with retry and concurrency."""

import time
import threading
import random
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List

from core.db import save_account, save_task_log
from core.config import Config


class TaskRunner:
    """Orchestrates Kiro registration tasks."""

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self._stop_flag = False

    def stop(self):
        """Signal all running tasks to stop."""
        self._stop_flag = True

    def run_registration(
        self,
        count: int = 1,
        concurrency: int = 1,
        email: Optional[str] = None,
        proxy: Optional[str] = None,
        headless: bool = True,
        provider_override: Optional[str] = None,
    ) -> dict:
        """Run registration task(s). Returns summary dict."""
        self.logger.info(f"Starting registration: count={count}, concurrency={concurrency}")

        success = 0
        failures = 0
        results: List[dict] = []

        max_workers = min(concurrency, count, self.config.max_concurrent)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = []
            for i in range(count):
                if self._stop_flag:
                    break
                future = pool.submit(
                    self._do_one_registration,
                    index=i,
                    total=count,
                    email=email,
                    proxy=proxy,
                    headless=headless,
                    provider_override=provider_override,
                )
                futures.append(future)

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result.get("ok"):
                        success += 1
                    else:
                        failures += 1
                    results.append(result)
                except Exception as e:
                    failures += 1
                    self.logger.error(f"Task thread error: {e}")
                    results.append({"ok": False, "error": str(e)})

        summary = {
            "total": count,
            "success": success,
            "failures": failures,
            "results": results,
        }
        self.logger.info(f"Registration complete: {success} success, {failures} failed")
        return summary

    def _do_one_registration(
        self,
        index: int,
        total: int,
        email: Optional[str],
        proxy: Optional[str],
        headless: bool,
        provider_override: Optional[str],
    ) -> dict:
        """Execute a single registration attempt with retry."""
        start_time = time.time()

        # Apply delay between registrations
        if index > 0 and self.config.register_delay > 0:
            delay = self.config.register_delay + random.uniform(-5, 10)
            delay = max(5, delay)
            self.logger.info(f"[{index+1}/{total}] Waiting {delay:.1f}s before next registration")
            time.sleep(delay)

        # Get proxy
        actual_proxy = proxy or self._get_proxy()

        # Try with retry
        last_error = ""
        for attempt in range(self.config.retry_times):
            if self._stop_flag:
                return {"ok": False, "error": "Stopped by user"}

            try:
                self.logger.info(
                    f"[{index+1}/{total}] Attempt {attempt+1}/{self.config.retry_times}"
                )
                result = self._execute_registration(
                    email=email,
                    proxy=actual_proxy,
                    headless=headless,
                    provider_override=provider_override,
                )

                if result.get("ok"):
                    duration = time.time() - start_time
                    save_task_log(
                        email=result.get("email", ""),
                        status="success",
                        email_provider=result.get("provider", ""),
                        duration=duration,
                    )
                    self.logger.info(
                        f"[{index+1}/{total}] SUCCESS: {result.get('email', '')} "
                        f"({duration:.1f}s)"
                    )
                    return result

                last_error = result.get("error", "Unknown error")
                self.logger.warning(
                    f"[{index+1}/{total}] Attempt {attempt+1} failed: {last_error}"
                )

            except Exception as e:
                last_error = str(e)
                self.logger.warning(
                    f"[{index+1}/{total}] Attempt {attempt+1} exception: {e}"
                )

            # Wait before retry
            if attempt < self.config.retry_times - 1:
                wait = random.uniform(5, 15)
                time.sleep(wait)

        # All retries exhausted
        duration = time.time() - start_time
        save_task_log(
            email=email or "",
            status="failed",
            error=last_error,
            duration=duration,
        )
        self.logger.error(f"[{index+1}/{total}] FAILED after {self.config.retry_times} attempts")
        return {"ok": False, "error": last_error}

    def _execute_registration(
        self,
        email: Optional[str],
        proxy: Optional[str],
        headless: bool,
        provider_override: Optional[str],
    ) -> dict:
        """Core registration logic with free email + Kiro register."""
        from email_providers import get_email_provider
        from kiro.register import KiroRegister

        # 1. Get free email
        providers_to_try = (
            [provider_override] if provider_override
            else list(self.config.email_providers)
        )

        mail_account = None
        used_provider = ""

        for provider_name in providers_to_try:
            try:
                provider = get_email_provider(provider_name, self.config)
                mail_account = provider.create_email()
                used_provider = provider_name
                self.logger.info(f"Email ready: {mail_account.email} ({provider_name})")
                break
            except Exception as e:
                self.logger.warning(f"Email provider '{provider_name}' failed: {e}")
                continue

        if not mail_account:
            return {"ok": False, "error": "All email providers failed"}

        actual_email = email or mail_account.email

        # 2. Register on Kiro
        reg = KiroRegister(proxy=proxy, headless=headless)
        reg.log_fn = lambda msg: self.logger.info(msg)

        # Keep reference to same provider instance for OTP polling
        # (avoids losing auth token when re-creating provider)
        _otp_provider = provider

        def otp_callback():
            """Poll for OTP from email provider."""
            self.logger.info("Waiting for verification code...")
            code = _otp_provider.wait_for_code(
                mail_account,
                timeout=self.config.otp_timeout,
            )
            if code:
                self.logger.info(f"Verification code received: {code}")
            return code

        ok, info = reg.register(
            email=actual_email,
            otp_callback=otp_callback,
        )

        if not ok:
            return {"ok": False, "error": info.get("error", "Registration failed")}

        # 3. Save account
        account_id = save_account(
            email=info["email"],
            password=info["password"],
            tokens=info,
            email_provider=used_provider,
        )

        # 4. Auto-switch if enabled
        if self.config.auto_switch:
            try:
                from kiro.switch import switch_kiro_account_local
                switch_kiro_account_local(info)
                self.logger.info("Auto-switched Kiro IDE to new account")
            except Exception as e:
                self.logger.warning(f"Auto-switch failed: {e}")

        return {
            "ok": True,
            "email": info["email"],
            "account_id": account_id,
            "provider": used_provider,
            "tokens": info,
        }

    def _get_proxy(self) -> Optional[str]:
        """Get next proxy from pool (if enabled)."""
        if not self.config.proxy_enabled:
            return None

        proxies = list(self.config.proxy_urls)

        # Load from file if specified
        if self.config.proxy_file:
            try:
                from pathlib import Path
                pf = Path(self.config.proxy_file)
                if pf.exists():
                    lines = pf.read_text().strip().splitlines()
                    proxies.extend([l.strip() for l in lines if l.strip()])
            except Exception:
                pass

        if not proxies:
            return None

        return random.choice(proxies)
