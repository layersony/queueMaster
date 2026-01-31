from rest_framework import serializers
from .models import Job, JobStatus

class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['task_type', 'payload', 'priority', 'scheduled_at', 'max_retries']
        extra_kwargs = {
            'scheduled_at': {'required': False},
            'max_retries': {'default': 3}
        }

class JobResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'task_type', 'status', 'priority', 'created_at', 
                  'retry_count', 'result', 'error_message']


