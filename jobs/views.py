from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Job, JobStatus, JobLog
from .serializers import JobCreateSerializer, JobResponseSerializer
from .queue_client import JobQueue

class JobViewSet(viewsets.ViewSet):
    """
    POST /jobs/ - Submit new job
    GET /jobs/{id}/ - Check status
    GET /jobs/{id}/retry - Manual retry
    GET /jobs/stats/ - Queue statistics
    """
    
    def create(self, request):
        serializer = JobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Rate limiting check (per user/IP)
        if not self.check_rate_limit(request):
            return Response(
                {'error': 'Rate limit exceeded'}, 
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        job = serializer.save(status=JobStatus.QUEUED)
        
        # Add to Redis queue
        queue = JobQueue()
        delay = None
        if job.scheduled_at:
            delay = int((job.scheduled_at - timezone.now()).total_seconds())
            delay = max(0, delay)
        
        queue.enqueue(str(job.id), job.priority, delay=delay)
        
        JobLog.objects.create(
            job=job,
            action='queued',
            message=f'Job queued with priority {job.priority}'
        )
        
        return Response(
            JobResponseSerializer(job).data, 
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, pk=None):
        job = get_object_or_404(Job, pk=pk)
        return Response(JobResponseSerializer(job).data)
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Manually retry a failed job"""
        job = get_object_or_404(Job, pk=pk)
        
        if job.status not in [JobStatus.FAILED, JobStatus.DEAD_LETTER]:
            return Response(
                {'error': 'Only failed jobs can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        job.status = JobStatus.QUEUED
        job.retry_count = 0
        job.error_message = None
        job.save()
        
        queue = JobQueue()
        queue.enqueue(str(job.id), job.priority)
        
        return Response({'status': 'job requeued'})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """System-wide statistics"""
        queue = JobQueue()
        db_stats = Job.objects.values('status').annotate(count=models.Count('id'))
        
        return Response({
            'redis': queue.get_queue_stats(),
            'database': {item['status']: item['count'] for item in db_stats},
            'workers': self.get_worker_status()
        })
    
    def check_rate_limit(self, request):
        # Implement token bucket or use django-ratelimit
        # Simplified example:
        key = f"rate_limit:{request.user.id or request.META.get('REMOTE_ADDR')}"
        pipe = JobQueue().redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)
        results = pipe.execute()
        return results[0] <= 100  # 100 req/min
    
    def get_worker_status(self):
        # Check active workers via Redis or heartbeat
        return {'active': 3, 'idle': 1}  # Placeholder

