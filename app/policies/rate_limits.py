from collections import defaultdict
import time


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, max_calls: int, period_seconds: int):
        self.max_calls = max_calls
        self.period = period_seconds
        self.calls = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.time()
        # Remove old calls
        self.calls[key] = [t for t in self.calls[key] if now - t < self.period]
        if len(self.calls[key]) >= self.max_calls:
            return False
        self.calls[key].append(now)
        return True