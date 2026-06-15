from __future__ import annotations

import asyncio
import time


class RateLimiter:
    def __init__(self, domain: str, delay_seconds: float = 1.5) -> None:
        self.domain = domain
        self.delay_seconds = delay_seconds
        self._lock = asyncio.Lock()
        self._next_request_at = 0.0
        self._cooldown_until = 0.0

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if now < self._cooldown_until:
                await asyncio.sleep(self._cooldown_until - now)
                now = time.monotonic()

            if now < self._next_request_at:
                await asyncio.sleep(self._next_request_at - now)
                now = time.monotonic()

            self._next_request_at = now + self.delay_seconds

    def backoff(self, seconds: float = 60.0) -> None:
        self._cooldown_until = max(self._cooldown_until, time.monotonic() + seconds)

    def next_available(self) -> float:
        return max(self._next_request_at, self._cooldown_until)
