import re


class SafetyChecker:
    """Checks for dangerous patterns in agent outputs or tool calls."""

    DANGEROUS_PATTERNS = [
        r"(?i)(delete|drop|truncate)\s+(table|database)",
        r"(?i)(rm|remove)\s+-rf\s+/",
        r"(?i)password\s*=\s*['\"].+['\"]",
    ]

    @classmethod
    def is_dangerous(cls, text: str) -> bool:
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text):
                return True
        return False

    @classmethod
    def require_confirmation(cls, action: str) -> bool:
        """Return True if action needs user confirmation."""
        return cls.is_dangerous(action)