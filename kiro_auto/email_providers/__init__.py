"""Free email providers for automated registration."""

from email_providers.base import BaseEmailProvider, EmailAccount
from core.config import Config


def get_email_provider(name: str, config: Config) -> BaseEmailProvider:
    """Factory: get email provider instance by name."""
    proxy = None
    if config.proxy_enabled and config.proxy_urls:
        import random
        proxy = random.choice(config.proxy_urls)

    if name == "onesecmail":
        from email_providers.onesecmail import OneSecMailProvider
        return OneSecMailProvider(proxy=proxy)
    elif name == "mail_tm":
        from email_providers.mail_tm import MailTmProvider
        return MailTmProvider(proxy=proxy)
    elif name == "tempmail_lol":
        from email_providers.tempmail_lol import TempMailLolProvider
        return TempMailLolProvider(proxy=proxy)
    elif name == "guerrilla":
        from email_providers.guerrilla import GuerrillaProvider
        return GuerrillaProvider(proxy=proxy)
    elif name == "cfworker":
        from email_providers.cfworker import CfWorkerProvider
        return CfWorkerProvider(
            api_url=config.cfworker_api_url,
            domain=config.cfworker_domain,
            proxy=proxy,
        )
    else:
        raise ValueError(f"Unknown email provider: {name}")
