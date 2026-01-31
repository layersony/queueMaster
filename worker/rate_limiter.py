import time
from functools import wraps

class RateLimiter:
    """Token bucket rate limiter using Redis"""
    
    def __init__(self, redis_client, key_prefix: str, max_tokens: int, refill_rate: float):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate  # tokens per second
    
    def is_allowed(self, identifier: str) -> bool:
        key = f"{self.key_prefix}:{identifier}"
        now = time.time()
        
        pipe = self.redis.pipeline()
        pipe.hmget(key, ['tokens', 'last_update'])
        pipe.exists(key)
        result = pipe.execute()
        
        tokens, last_update = result[0] if result[0] else (None, None)
        exists = result[1]
        
        if not exists or tokens is None:
            # Initialize bucket
            self.redis.hmset(key, {'tokens': self.max_tokens - 1, 'last_update': now})
            self.redis.expire(key, 3600)
            return True
        
        # Calculate refill
        tokens = float(tokens)
        last_update = float(last_update)
        time_passed = now - last_update
        new_tokens = min(self.max_tokens, tokens + time_passed * self.refill_rate)
        
        if new_tokens >= 1:
            self.redis.hmset(key, {'tokens': new_tokens - 1, 'last_update': now})
            return True
        else:
            self.redis.hmset(key, {'tokens': new_tokens, 'last_update': now})
            return False