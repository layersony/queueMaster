import random
from math import pow

class RetryHandler:
    @staticmethod
    def calculate_delay(retry_count: int, base_delay: int = 60, max_delay: int = 3600) -> int:
        """Exponential backoff with jitter"""
        # Exponential: 60s, 120s, 240s, 480s...
        delay = min(base_delay * (2 ** (retry_count - 1)), max_delay)
        # Add jitter (±20%) to prevent thundering herd
        jitter = random.uniform(0.8, 1.2)
        return int(delay * jitter)

