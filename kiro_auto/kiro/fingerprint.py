"""Browser fingerprint randomization for anti-detection."""

import random
from typing import Dict, Tuple


_UA_TEMPLATES = [
    {
        "name": "win_chrome",
        "template": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Safari/537.36",
    },
    {
        "name": "mac_chrome",
        "template": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{minor}_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Safari/537.36",
    },
    {
        "name": "linux_chrome",
        "template": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Safari/537.36",
    },
]

_LOCALE_TIMEZONE_POOLS = [
    ("en-US", ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"]),
    ("en-GB", ["Europe/London"]),
    ("en-CA", ["America/Toronto", "America/Vancouver"]),
    ("en-AU", ["Australia/Sydney", "Australia/Melbourne"]),
]

_VIEWPORT_PRESETS = [
    (1366, 768),
    (1440, 900),
    (1536, 864),
    (1600, 900),
    (1680, 1050),
    (1920, 1080),
]


def random_chrome_version() -> str:
    """Generate a realistic Chrome version string."""
    major = random.randint(130, 137)
    build = random.randint(6400, 7399)
    patch = random.randint(40, 220)
    return f"{major}.0.{build}.{patch}"


def build_random_profile() -> Dict:
    """Build a random browser profile for anti-fingerprinting."""
    ua_tmpl = random.choice(_UA_TEMPLATES)
    chrome_ver = random_chrome_version()

    locale, tz_pool = random.choice(_LOCALE_TIMEZONE_POOLS)
    timezone_id = random.choice(tz_pool)

    base_w, base_h = random.choice(_VIEWPORT_PRESETS)
    width = max(1100, base_w + random.randint(-72, 72))
    height = max(700, base_h + random.randint(-54, 54))

    if ua_tmpl["name"] == "mac_chrome":
        os_minor = random.choice([14, 15, 16])
        user_agent = ua_tmpl["template"].format(ver=chrome_ver, minor=os_minor)
    else:
        user_agent = ua_tmpl["template"].format(ver=chrome_ver)

    return {
        "name": f"{ua_tmpl['name']}_{chrome_ver}",
        "user_agent": user_agent,
        "locale": locale,
        "timezone_id": timezone_id,
        "viewport": {"width": width, "height": height},
        "color_scheme": random.choice(["light", "dark"]),
        "reduced_motion": random.choice(["reduce", "no-preference"]),
    }
