"""Base class for email providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Set


@dataclass
class EmailAccount:
    """Represents a temporary email account."""
    email: str
    account_id: str = ""
    token: str = ""
    extra: dict = field(default_factory=dict)


class BaseEmailProvider(ABC):
    """Abstract base for all email providers. All must be FREE."""

    name: str = "base"

    @abstractmethod
    def create_email(self) -> EmailAccount:
        """Create/get a new temporary email address. Must be FREE."""
        ...

    @abstractmethod
    def wait_for_code(
        self,
        account: EmailAccount,
        keyword: str = "",
        timeout: int = 120,
        code_pattern: Optional[str] = None,
    ) -> Optional[str]:
        """Wait for verification code in inbox. Returns code or None."""
        ...

    def get_current_ids(self, account: EmailAccount) -> Set[str]:
        """Get current message IDs (for before/after comparison)."""
        return set()

    def _extract_code(self, text: str, pattern: Optional[str] = None) -> Optional[str]:
        """Extract verification code from email text."""
        import re

        if not text:
            return None

        patterns = []
        if pattern:
            patterns.append(pattern)

        # Common verification code patterns
        patterns.extend([
            r"(?is)(?:verification\s+code|one[-\s]*time\s+(?:password|code)|security\s+code)[^0-9]{0,30}(\d{6})",
            r"(?is)\bcode\b[^0-9]{0,12}(\d{6})",
            r"(?<![a-zA-Z0-9])(\d{6})(?![a-zA-Z0-9])",
        ])

        for regex in patterns:
            m = re.search(regex, text)
            if m:
                return m.group(1) if m.groups() else m.group(0)
        return None
