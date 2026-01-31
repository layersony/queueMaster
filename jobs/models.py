import uuid
from django.db import models
from django.contrib.postgres.fields import JSONField

class JobStatus(models.TextChoices):
    PENDING = 'pending'
    QUEUED = 'queued'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    DEAD_LETTER = 'dead_letter'

class JobPriority(models.IntegerChoices):
    CRITICAL = 1, 'Critical'
    HIGH = 2, 'High'
    NORMAL = 3, 'Normal'
    LOW = 4, 'Low'

class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_type = models.CharField(max_length=100) 
    payload = models.JSONField() 
    status = models.CharField(
        max_length=20, 
        choices=JobStatus.choices, 
        default=JobStatus.PENDING
    )
    priority = models.IntegerField(
        choices=JobPriority.choices,
        default=JobPriority.NORMAL
    )
    
    # Retry logic
    max_retries = models.IntegerField(default=3)
    retry_count = models.IntegerField(default=0)
    retry_delay = models.IntegerField(default=60)  # seconds
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Result/Error tracking
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    worker_id = models.CharField(max_length=100, null=True, blank=True)

    dependencies = models.ManyToManyField('self', symmetrical=False, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'priority', 'created_at']),
            models.Index(fields=['scheduled_at', 'status']),
        ]
    
    def __str__(self):
        return f"{self.task_type}:{self.id}:{self.status}"
    
    def can_execute(self):
        """Check if all dependencies are completed"""
        return not self.dependencies.exclude(status=JobStatus.COMPLETED).exists()

class JobLog(models.Model):
    """Audit trail for job lifecycle"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50)
    message = models.TextField()
    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['job', '-timestamp']),
        ]