"""Configuration management - YAML based with sensible defaults."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


CONFIG_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.yaml"
DEFAULT_DB_PATH = CONFIG_DIR / "data" / "kiro_accounts.db"


@dataclass
class Config:
    """Application configuration with free-tier defaults."""

    # Paths
    config_path: str = str(DEFAULT_CONFIG_PATH)
    db_path: str = str(DEFAULT_DB_PATH)

    # Kiro registration
    headless: bool = True
    max_concurrent: int = 2
    retry_times: int = 3
    otp_timeout: int = 120
    register_delay: int = 30

    # Email providers (priority order) - ALL FREE
    email_providers: List[str] = field(default_factory=lambda: [
        "tempmail_lol",
        "mail_tm",
        "guerrilla",
        "cfworker",
    ])

    # Cloudflare Worker (self-hosted free)
    cfworker_api_url: str = ""
    cfworker_domain: str = ""

    # Proxy (optional)
    proxy_enabled: bool = False
    proxy_urls: List[str] = field(default_factory=list)
    proxy_file: str = ""

    # Schedule
    schedule_enabled: bool = True
    schedule_interval_minutes: int = 60
    schedule_max_per_run: int = 1

    # Auto-switch Kiro IDE
    auto_switch: bool = True
    auto_restart_ide: bool = False

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/kiro-auto.log"


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file, with env var overrides."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    config = Config()

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Kiro settings
        kiro = data.get("kiro", {})
        config.headless = kiro.get("headless", config.headless)
        config.max_concurrent = kiro.get("max_concurrent", config.max_concurrent)
        config.retry_times = kiro.get("retry_times", config.retry_times)
        config.otp_timeout = kiro.get("otp_timeout", config.otp_timeout)
        config.register_delay = kiro.get("register_delay", config.register_delay)

        # Email settings
        email = data.get("email", {})
        if email.get("providers"):
            config.email_providers = email["providers"]
        cfworker = email.get("cfworker", {})
        config.cfworker_api_url = cfworker.get("api_url", "")
        config.cfworker_domain = cfworker.get("domain", "")

        # Proxy settings
        proxy = data.get("proxy", {})
        config.proxy_enabled = proxy.get("enabled", False)
        config.proxy_urls = proxy.get("urls", [])
        config.proxy_file = proxy.get("file", "")

        # Schedule settings
        schedule = data.get("schedule", {})
        config.schedule_enabled = schedule.get("enabled", True)
        config.schedule_interval_minutes = schedule.get("interval_minutes", 60)
        config.schedule_max_per_run = schedule.get("max_accounts_per_run", 1)

        # Auto-switch
        auto_switch = data.get("auto_switch", {})
        config.auto_switch = auto_switch.get("enabled", True)
        config.auto_restart_ide = auto_switch.get("restart_ide", False)

        # Logging
        logging_cfg = data.get("logging", {})
        config.log_level = logging_cfg.get("level", "INFO")
        config.log_file = logging_cfg.get("file", "logs/kiro-auto.log")

    # Environment variable overrides
    config.headless = os.getenv("KIRO_HEADLESS", str(config.headless)).lower() in ("true", "1", "yes")
    config.proxy_enabled = os.getenv("KIRO_PROXY_ENABLED", str(config.proxy_enabled)).lower() in ("true", "1", "yes")

    if os.getenv("KIRO_PROXY_URL"):
        config.proxy_urls = [os.getenv("KIRO_PROXY_URL")]
        config.proxy_enabled = True

    if os.getenv("KIRO_CFWORKER_URL"):
        config.cfworker_api_url = os.getenv("KIRO_CFWORKER_URL")
    if os.getenv("KIRO_CFWORKER_DOMAIN"):
        config.cfworker_domain = os.getenv("KIRO_CFWORKER_DOMAIN")

    config.config_path = str(path)
    return config


def save_default_config(path: Optional[str] = None):
    """Generate default config.yaml file."""
    output_path = Path(path) if path else DEFAULT_CONFIG_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    default_yaml = """\
# Kiro Auto-Registration Configuration
# All services used are 100% FREE

kiro:
  headless: true              # true = headless browser (no window)
  max_concurrent: 2           # Max concurrent registrations
  retry_times: 3              # Retry count per registration
  otp_timeout: 120            # Seconds to wait for verification code
  register_delay: 30          # Seconds between registrations

email:
  providers:                  # Priority order (all FREE)
    - tempmail_lol            # TempMail.lol - free, no config needed
    - mail_tm                 # Mail.tm - free, no config needed
    - guerrilla               # Guerrilla Mail - free backup
    - cfworker                # Cloudflare Worker - self-hosted free
  cfworker:                   # Only if using Cloudflare Worker
    api_url: ""
    domain: ""

proxy:
  enabled: false
  urls: []                    # List of proxy URLs
  file: ""                    # Or file with proxies (one per line)

schedule:
  enabled: true
  interval_minutes: 60        # Run every 60 minutes
  max_accounts_per_run: 1     # Accounts to create per run

auto_switch:
  enabled: true               # Auto-switch Kiro IDE after registration
  restart_ide: false          # Auto-restart Kiro IDE

logging:
  level: INFO
  file: logs/kiro-auto.log
"""
    output_path.write_text(default_yaml, encoding="utf-8")
    return str(output_path)
