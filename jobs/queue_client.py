import json
import redis
from django.conf import settings
from datetime import datetime, timedelta
from typing import Optional

class JobQueue:
    """Redis-backed priority queue with scheduling support"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        self.QUEUE_KEY = "job_queue"
        self.SCHEDULED_KEY = "scheduled_jobs"
        self.DLQ_KEY = "dead_letter_queue"
        self.PROCESSING_KEY = "processing_jobs"
    
    def enqueue(self, job_id: str, priority: int, delay: Optional[int] = None):
        """Add job to queue or schedule it"""
        if delay:
            # Schedule for later using Redis sorted set (score = timestamp)
            execute_at = datetime.now() + timedelta(seconds=delay)
            self.redis_client.zadd(
                self.SCHEDULED_KEY,
                {str(job_id): execute_at.timestamp()}
            )
        else:
            # Use priority queue (lower score = higher priority)
            # Format: priority.timestamp to ensure FIFO within same priority
            score = priority * 10000000000 + datetime.now().timestamp()
            self.redis_client.zadd(self.QUEUE_KEY, {str(job_id): score})
    
    def dequeue(self, timeout: int = 5) -> Optional[str]:
        """Get next job with blocking support"""
        # First, move any due scheduled jobs to main queue
        self._promote_due_jobs()
        
        # Pop from priority queue (lowest score first)
        result = self.redis_client.zpopmin(self.QUEUE_KEY, count=1)
        if result:
            job_id = result[0][0]
            # Track as processing (with TTL for cleanup if worker dies)
            self.redis_client.setex(
                f"{self.PROCESSING_KEY}:{job_id}", 
                3600,  # 1 hour TTL
                datetime.now().isoformat()
            )
            return job_id
        return None
    
    def _promote_due_jobs(self):
        """Move scheduled jobs that are due to the main queue"""
        now = datetime.now().timestamp()
        due_jobs = self.redis_client.zrangebyscore(
            self.SCHEDULED_KEY, 0, now, withscores=True
        )
        
        for job_id, score in due_jobs:
            # Remove from scheduled
            self.redis_client.zrem(self.SCHEDULED_KEY, job_id)
            # Add to main queue (score = priority)
            self.redis_client.zadd(self.QUEUE_KEY, {job_id: score})
    
    def complete(self, job_id: str):
        """Mark job as completed"""
        self.redis_client.delete(f"{self.PROCESSING_KEY}:{job_id}")
        self.redis_client.zrem(self.QUEUE_KEY, job_id)
    
    def requeue(self, job_id: str, priority: int, delay: int = 0):
        """Put job back for retry with optional delay"""
        self.redis_client.delete(f"{self.PROCESSING_KEY}:{job_id}")
        self.enqueue(job_id, priority, delay=delay)
    
    def move_to_dlq(self, job_id: str, error_info: dict):
        """Move to dead letter queue after max retries"""
        self.redis_client.delete(f"{self.PROCESSING_KEY}:{job_id}")
        self.redis_client.zrem(self.QUEUE_KEY, job_id)
        self.redis_client.lpush(
            self.DLQ_KEY, 
            json.dumps({'job_id': job_id, 'error': error_info, 'timestamp': datetime.now().isoformat()})
        )
    
    def get_queue_stats(self) -> dict:
        """Metrics for monitoring"""
        return {
            'queued': self.redis_client.zcard(self.QUEUE_KEY),
            'scheduled': self.redis_client.zcard(self.SCHEDULED_KEY),
            'processing': len(self.redis_client.keys(f"{self.PROCESSING_KEY}:*")),
            'dead_letter': self.redis_client.llen(self.DLQ_KEY),
        }