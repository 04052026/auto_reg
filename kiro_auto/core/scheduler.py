"""Scheduler - Runs registration tasks on a cron-like interval."""

import time
import threading
import logging
from typing import Optional

from core.config import Config
from core.task_runner import TaskRunner


class Scheduler:
    """Periodically triggers registration tasks."""

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._runner: Optional[TaskRunner] = None

    def start(self, interval_minutes: int = 60, max_per_run: int = 1):
        """Start the scheduler loop (blocking)."""
        self._running = True
        self._runner = TaskRunner(self.config, self.logger)
        interval_seconds = interval_minutes * 60

        self.logger.info(
            f"Scheduler started: every {interval_minutes} min, "
            f"max {max_per_run} accounts/run"
        )
        print(f"\n=== Kiro Auto-Reg Scheduler ===")
        print(f"Interval: {interval_minutes} minutes")
        print(f"Max per run: {max_per_run}")
        print(f"Press Ctrl+C to stop\n")

        # Run immediately on first start
        self._run_once(max_per_run)

        while self._running:
            self.logger.info(f"Next run in {interval_minutes} minutes...")
            # Sleep in chunks so we can respond to stop signal quickly
            for _ in range(interval_seconds):
                if not self._running:
                    break
                time.sleep(1)

            if self._running:
                self._run_once(max_per_run)

        self.logger.info("Scheduler stopped")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._runner:
            self._runner.stop()
        self.logger.info("Scheduler stop requested")

    def _run_once(self, count: int):
        """Execute one registration cycle."""
        self.logger.info(f"Running scheduled registration (count={count})")
        try:
            result = self._runner.run_registration(
                count=count,
                concurrency=1,
                headless=self.config.headless,
            )
            success = result.get("success", 0)
            failures = result.get("failures", 0)
            self.logger.info(
                f"Scheduled run complete: {success} success, {failures} failed"
            )
        except Exception as e:
            self.logger.error(f"Scheduled run error: {e}")
