import os
import sys
import json
import time
import signal
import logging
from datetime import datetime
from typing import Dict, Type
from redis.exceptions import RedisError
import django

sys.path.append('/app/django_api')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from jobs.models import Job, JobStatus, JobLog
from jobs.queue_client import JobQueue
from processors import TaskProcessorRegistry
from retry import RetryHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Worker:
    def __init__(self, worker_id: str, poll_interval: float = 1.0):
        self.worker_id = worker_id
        self.poll_interval = poll_interval
        self.queue = JobQueue()
        self.running = True
        self.current_job = None
        
        # Graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        logger.info(f"Worker {self.worker_id} shutting down...")
        self.running = False
        if self.current_job:
            # Return job to queue if interrupted
            self.queue.requeue(self.current_job.id, self.current_job.priority)
    
    def run(self):
        logger.info(f"Worker {self.worker_id} started")
        
        while self.running:
            try:
                job_id = self.queue.dequeue(timeout=self.poll_interval)
                
                if job_id:
                    self.process_job(job_id)
                else:
                    # No jobs available, small sleep to prevent CPU spinning
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(1)
    
    def process_job(self, job_id: str):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            logger.error(f"Job {job_id} not found in DB")
            self.queue.complete(job_id)
            return
        
        self.current_job = job
        
        # Update status
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now()
        job.worker_id = self.worker_id
        job.save()
        
        JobLog.objects.create(
            job=job,
            action='started',
            message=f'Processing by worker {self.worker_id}',
            metadata={'worker_id': self.worker_id}
        )
        
        try:
            # Execute task
            processor = TaskProcessorRegistry.get(job.task_type)
            result = processor.execute(job.payload)
            
            # Success
            job.status = JobStatus.COMPLETED
            job.result = result
            job.completed_at = datetime.now()
            job.save()
            
            self.queue.complete(job_id)
            
            JobLog.objects.create(
                job=job,
                action='completed',
                message='Job completed successfully',
                metadata={'result': result}
            )
            
            logger.info(f"Job {job_id} completed")
            
        except Exception as e:
            self._handle_failure(job, str(e))
        
        finally:
            self.current_job = None
    
    def _handle_failure(self, job: Job, error: str):
        job.retry_count += 1
        job.error_message = error[:500]  # Truncate long errors
        
        if job.retry_count >= job.max_retries:
            # Move to DLQ
            job.status = JobStatus.DEAD_LETTER
            job.save()
            
            self.queue.move_to_dlq(
                str(job.id), 
                {'error': error, 'retries': job.retry_count}
            )
            
            JobLog.objects.create(
                job=job,
                action='dead_letter',
                message=f'Failed after {job.retry_count} retries: {error}'
            )
            logger.error(f"Job {job.id} moved to DLQ: {error}")
        else:
            # Retry with exponential backoff
            retry_delay = RetryHandler.calculate_delay(job.retry_count)
            job.status = JobStatus.QUEUED
            job.save()
            
            self.queue.requeue(str(job.id), job.priority, delay=retry_delay)
            
            JobLog.objects.create(
                job=job,
                action='retry_scheduled',
                message=f'Retry {job.retry_count}/{job.max_retries} in {retry_delay}s',
                metadata={'error': error, 'delay': retry_delay}
            )
            logger.warning(f"Job {job.id} retry scheduled: {error}")

if __name__ == "__main__":
    import uuid
    worker_id = os.environ.get('WORKER_ID', str(uuid.uuid4())[:8])
    worker = Worker(worker_id)
    worker.run()