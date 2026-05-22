"""Exponential backoff with jitter for API retries"""
import time
import random
from typing import Optional
from golike_core.logging import logger


class ExponentialBackoff:
    """
    Exponential backoff with jitter.

    Delays follow the pattern:
    - Attempt 1: 1-2s
    - Attempt 2: 2-5s
    - Attempt 3: 4-13s
    - Attempt 4: 8-25s (capped at max_delay)

    Attributes:
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay cap (default: 60.0)
        jitter: Jitter factor (default: 0.5 = ±50%)
        max_retries: Maximum number of retries (default: 5)
        attempt: Current attempt counter
    """

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: float = 0.5,
        max_retries: int = 5
    ):
        """
        Initialize ExponentialBackoff.

        Args:
            base_delay: Base delay in seconds
            max_delay: Maximum delay cap
            jitter: Jitter factor (0.0-1.0)
            max_retries: Maximum number of retry attempts
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.max_retries = max_retries
        self.attempt = 0

    def sleep(self) -> None:
        """
        Sleep with exponential backoff and jitter.

        Formula: delay = min(base * 2^attempt, max_delay) ± jitter
        """
        if self.attempt >= self.max_retries:
            logger.warning(f"Exceeded max retries ({self.max_retries})")
            return

        # Exponential: base * 2^attempt
        delay = self.base_delay * (2 ** self.attempt)

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter (±percentage)
        if self.jitter > 0:
            jitter_range = delay * self.jitter
            delay = max(0.1, delay + random.uniform(-jitter_range, jitter_range))

        logger.debug(
            f"Backoff attempt {self.attempt + 1}/{self.max_retries}, "
            f"sleeping {delay:.1f}s"
        )
        time.sleep(delay)
        self.attempt += 1

    def reset(self) -> None:
        """Reset attempt counter"""
        self.attempt = 0

    def get_delay(self) -> float:
        """
        Get next delay without sleeping.

        Returns:
            Next delay in seconds
        """
        if self.attempt >= self.max_retries:
            return 0.0

        delay = self.base_delay * (2 ** self.attempt)
        delay = min(delay, self.max_delay)

        if self.jitter > 0:
            jitter_range = delay * self.jitter
            delay = max(0.1, delay + random.uniform(-jitter_range, jitter_range))

        return delay
