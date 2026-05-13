# Kiro Auto-Registration Tool

Automated Kiro (AWS Builder ID) account registration - **100% FREE**, no paid services required.

## Features

- **Free Email**: Auto-generates temporary emails (TempMail.lol, Mail.tm, Guerrilla Mail)
- **Auto OTP**: Automatically extracts verification codes from emails
- **Auto Retry**: Failed? Retries with different email provider/proxy
- **Auto Rotate**: Email provider fails → switches to next provider
- **Auto Schedule**: Runs on a timer (every N minutes/hours)
- **Auto Switch**: Registers → immediately switches Kiro IDE to new account
- **Anti-Detection**: Random browser fingerprints, human-like typing
- **Zero Cost**: No paid APIs, no subscriptions, no credits needed

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Register a single account
python main.py register

# Register 5 accounts
python main.py register -n 5

# Run scheduler (auto-register every hour)
python main.py schedule --interval 60

# List registered accounts
python main.py list

# Switch Kiro IDE to account #3
python main.py switch 3

# Refresh tokens
python main.py refresh
```

## Configuration

Edit `config.yaml` to customize:

```yaml
kiro:
  headless: true          # Hide browser
  retry_times: 3          # Retries per registration
  otp_timeout: 120        # Seconds to wait for code

email:
  providers:              # Priority order (all free)
    - tempmail_lol
    - mail_tm
    - guerrilla

schedule:
  enabled: true
  interval_minutes: 60    # Auto-register every hour
```

## Email Providers (All FREE)

| Provider | Config Needed | Notes |
|----------|--------------|-------|
| TempMail.lol | None | Default, instant |
| Mail.tm | None | Good backup |
| Guerrilla Mail | None | Reliable fallback |
| CF Worker | api_url, domain | Self-hosted, cleanest |

## Docker

```bash
docker build -t kiro-auto .
docker run -d --name kiro-auto kiro-auto
```

## Architecture

```
main.py (CLI)
  → TaskRunner (concurrency, retry)
    → EmailProvider (auto-rotate: tempmail → mail_tm → guerrilla)
    → KiroRegister (Playwright headless, random fingerprint)
    → SQLite DB (persist accounts + tokens)
    → Auto-switch Kiro IDE
```

## Requirements

- Python 3.10+
- ~500MB RAM (for headless browser)
- Internet connection
- Optional: Proxy (if IP gets rate-limited)

## Cost: $0

Everything is free. No API keys, no credits, no subscriptions.
