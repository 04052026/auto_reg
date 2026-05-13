#!/usr/bin/env python3
"""
Kiro Auto-Registration Tool
Standalone CLI tool for automated Kiro (AWS Builder ID) account registration.
100% FREE - No paid services required.
"""

import argparse
import sys
import signal
import os
from pathlib import Path

# Ensure package-level imports resolve correctly when running as script
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from core.config import load_config
from core.db import init_db
from core.logger import setup_logger
from core.task_runner import TaskRunner
from core.scheduler import Scheduler


def main():
    parser = argparse.ArgumentParser(
        description="Kiro Auto-Registration Tool - FREE automated account creation"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # register command
    reg_parser = subparsers.add_parser("register", help="Register new Kiro account(s)")
    reg_parser.add_argument("-n", "--count", type=int, default=1, help="Number of accounts to register")
    reg_parser.add_argument("-c", "--concurrency", type=int, default=1, help="Concurrent registrations")
    reg_parser.add_argument("--email", type=str, default=None, help="Specific email (optional)")
    reg_parser.add_argument("--proxy", type=str, default=None, help="Proxy URL (optional)")
    reg_parser.add_argument("--headless", action="store_true", default=True, help="Run browser headless")
    reg_parser.add_argument("--no-headless", action="store_true", help="Show browser window")
    reg_parser.add_argument("--provider", type=str, default=None, help="Email provider override")

    # schedule command
    sched_parser = subparsers.add_parser("schedule", help="Run scheduled auto-registration")
    sched_parser.add_argument("--interval", type=int, default=60, help="Interval in minutes")
    sched_parser.add_argument("--max-per-run", type=int, default=1, help="Max accounts per run")

    # list command
    subparsers.add_parser("list", help="List registered accounts")

    # switch command
    switch_parser = subparsers.add_parser("switch", help="Switch Kiro IDE to an account")
    switch_parser.add_argument("account_id", type=int, help="Account ID to switch to")

    # refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Refresh token for an account")
    refresh_parser.add_argument("account_id", type=int, nargs="?", help="Account ID (latest if omitted)")

    # status command
    subparsers.add_parser("status", help="Show system status")

    # config command
    subparsers.add_parser("config", help="Show/edit configuration")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Initialize
    config = load_config()
    logger = setup_logger(config)
    init_db()

    # Handle commands
    if args.command == "register":
        headless = not args.no_headless
        runner = TaskRunner(config, logger)
        runner.run_registration(
            count=args.count,
            concurrency=args.concurrency,
            email=args.email,
            proxy=args.proxy,
            headless=headless,
            provider_override=args.provider,
        )

    elif args.command == "schedule":
        scheduler = Scheduler(config, logger)

        # Graceful shutdown via flag (signal handlers just set flag)
        def _signal_handler(*_):
            scheduler.stop()

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        try:
            scheduler.start(
                interval_minutes=args.interval,
                max_per_run=args.max_per_run,
            )
        except KeyboardInterrupt:
            scheduler.stop()
            logger.info("Scheduler interrupted by user")

    elif args.command == "list":
        from core.db import list_accounts
        accounts = list_accounts()
        if not accounts:
            print("No registered accounts found.")
            return
        print(f"\n{'ID':<5} {'Email':<40} {'Status':<12} {'Created':<20}")
        print("-" * 80)
        for acc in accounts:
            print(f"{acc['id']:<5} {acc['email']:<40} {acc['status']:<12} {acc['created_at']:<20}")
        print(f"\nTotal: {len(accounts)} accounts")

    elif args.command == "switch":
        from kiro.switch import switch_to_account
        success = switch_to_account(args.account_id)
        if success:
            print(f"Successfully switched Kiro IDE to account #{args.account_id}")
        else:
            print(f"Failed to switch to account #{args.account_id}")
            sys.exit(1)

    elif args.command == "refresh":
        from kiro.token_manager import refresh_account_token
        account_id = args.account_id
        success = refresh_account_token(account_id)
        if success:
            print("Token refreshed successfully")
        else:
            print("Token refresh failed")
            sys.exit(1)

    elif args.command == "status":
        from core.db import get_stats
        stats = get_stats()
        print("\n=== Kiro Auto-Reg Status ===")
        print(f"Total accounts: {stats['total']}")
        print(f"Active: {stats['active']}")
        print(f"Expired: {stats['expired']}")
        print(f"Last registration: {stats['last_created']}")
        print()

    elif args.command == "config":
        print(f"Config file: {config.config_path}")
        print(f"Database: {config.db_path}")
        print(f"Email providers: {', '.join(config.email_providers)}")
        print(f"Headless: {config.headless}")
        print(f"Schedule enabled: {config.schedule_enabled}")


if __name__ == "__main__":
    main()
