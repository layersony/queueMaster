from django.db import models
from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from jobs.models import Job, JobLog, JobStatus
from jobs.queue_client import JobQueue
import json

class DashboardView(TemplateView):
    template_name = 'dashboard.html'

class DashboardAPI:
    @staticmethod
    def get_stats(request):
        """Endpoint for AJAX polling"""
        queue = JobQueue()
        redis_stats = queue.get_queue_stats()
        
        # Time-based aggregation (last 24h)
        time_threshold = timezone.now() - timedelta(hours=24)
        
        db_stats = {
            'total_24h': Job.objects.filter(created_at__gte=time_threshold).count(),
            'completed_24h': Job.objects.filter(
                status=JobStatus.COMPLETED, 
                completed_at__gte=time_threshold
            ).count(),
            'failed_24h': Job.objects.filter(
                status=JobStatus.FAILED,
                updated_at__gte=time_threshold
            ).count(),
            'avg_processing_time': Job.objects.filter(
                status=JobStatus.COMPLETED,
                completed_at__gte=time_threshold,
                started_at__isnull=False
            ).exclude(completed_at__isnull=True).aggregate(
                avg_time=models.Avg(models.F('completed_at') - models.F('started_at'))
            )['avg_time']
        }
        
        # Worker status from Redis keys
        worker_keys = queue.redis_client.keys("worker:*:heartbeat")
        workers = []
        for key in worker_keys:
            worker_id = key.split(':')[1]
            last_seen = queue.redis_client.get(key)
            workers.append({
                'id': worker_id,
                'status': 'active' if last_seen else 'stale',
                'last_seen': last_seen
            })
        
        return JsonResponse({
            'redis': redis_stats,
            'db': db_stats,
            'workers': workers,
            'timestamp': timezone.now().isoformat()
        })

    @staticmethod
    def get_jobs(request):
        """Paginated job list with filters"""
        status = request.GET.get('status', '')
        task_type = request.GET.get('task_type', '')
        priority = request.GET.get('priority', '')
        page = int(request.GET.get('page', 1))
        per_page = 50
        
        queryset = Job.objects.all().order_by('-created_at')
        
        if status:
            queryset = queryset.filter(status=status)
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        if priority:
            queryset = queryset.filter(priority=int(priority))
        
        total = queryset.count()
        start = (page - 1) * per_page
        jobs = queryset[start:start + per_page]
        
        return JsonResponse({
            'jobs': [
                {
                    'id': str(j.id),
                    'task_type': j.task_type,
                    'status': j.status,
                    'priority': j.priority,
                    'retry_count': j.retry_count,
                    'created_at': j.created_at.isoformat(),
                    'worker_id': j.worker_id,
                    'error_message': j.error_message[:100] if j.error_message else None
                }
                for j in jobs
            ],
            'total': total,
            'pages': (total // per_page) + 1,
            'current_page': page
        })

    @staticmethod
    def get_job_details(request, job_id):
        job = Job.objects.get(id=job_id)
        logs = JobLog.objects.filter(job=job).order_by('timestamp')
        
        return JsonResponse({
            'job': {
                'id': str(job.id),
                'task_type': job.task_type,
                'payload': job.payload,
                'status': job.status,
                'priority': job.priority,
                'retry_count': job.retry_count,
                'max_retries': job.max_retries,
                'created_at': job.created_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'worker_id': job.worker_id,
                'result': job.result,
                'error_message': job.error_message,
            },
            'logs': [
                {
                    'timestamp': log.timestamp.isoformat(),
                    'action': log.action,
                    'message': log.message
                }
                for log in logs
            ]
        })

    @staticmethod
    def get_dlq_jobs(request):
        """Get Dead Letter Queue contents"""
        queue = JobQueue()
        dlq_data = queue.redis_client.lrange(queue.DLQ_KEY, 0, 99)
        jobs = [json.loads(item) for item in dlq_data]
        
        # Enrich with DB data
        for item in jobs:
            try:
                job = Job.objects.get(id=item['job_id'])
                item['task_type'] = job.task_type
                item['created_at'] = job.created_at.isoformat()
            except Job.DoesNotExist:
                item['task_type'] = 'unknown'
                item['created_at'] = None
                
        return JsonResponse({'jobs': jobs})

# monitoring/urls.py
