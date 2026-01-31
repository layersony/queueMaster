# QueueMaster - Scalable Job Processing System

[![Django](https://img.shields.io/badge/Django-4.2-green)](https://www.djangoproject.com/)
[![Redis](https://img.shields.io/badge/Redis-7-red)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade, scalable asynchronous job processing system built with Django REST Framework and Redis. Features priority queues, scheduled jobs, automatic retries with exponential backoff, dead letter queues, and a real-time monitoring dashboard.

## Key Features

- **REST API** - Submit and manage jobs via RESTful endpoints
- **Priority Queues** - 4-tier priority system (Critical &gt; High &gt; Normal &gt; Low)
- **Scheduled Execution** - Delayed job execution with precise scheduling
- **Reliable Processing** - At-least-once delivery with automatic retries
- **Dead Letter Queue** - Failed job isolation for manual inspection
- **Horizontal Scaling** - Stateless workers that scale via Docker
- **Real-time Dashboard** - Web-based monitoring with auto-refresh
- **Circuit Breaker** - Automatic failure detection and recovery
- **Rate Limiting** - Token-bucket algorithm for API and worker protection

## Architecture
```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │──────▶  Django API  │──────▶   Redis     │
│  (Mobile/   │      │  (REST API)  │      │   Queue     │
│   Web/CLI)  │      └──────────────┘      └──────┬──────┘
└─────────────┘                                   │
│
┌──────────────────────┼──────────────────────┐
│                      │                      │
┌──────▼──────┐        ┌──────▼──────┐        ┌──────▼──────┐
│  Worker 1   │        │  Worker 2   │        │  Worker N   │
│  (Docker)   │        │  (Docker)   │        │  (Docker)   │
└──────┬──────┘        └──────┬──────┘        └──────┬──────┘
│                      │                      │
└──────────────────────┼──────────────────────┘
│
┌──────▼──────┐
│  PostgreSQL │
│   (State)   │
└─────────────┘
```


## Tech Stack

- **Backend**: Django 4.2 + Django REST Framework
- **Queue**: Redis (Sorted Sets for priority, Lists for DLQ)
- **Database**: PostgreSQL 15+ (Job persistence & audit logs)
- **Workers**: Python async processors with heartbeat monitoring
- **Frontend**: Tailwind CSS + Chart.js (Dark mode dashboard)
- **Deployment**: Docker Compose / Kubernetes ready

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+ (for local development)
- Make (optional, for commands)

### 1. Clone & Configure

```bash
git clone https://github.com/your-org/queuemaster.git
cd queuemaster

# Copy environment template
cp .env.example .env
# Edit .env with your secrets
```

### 2. Docker Deployment (Production)

```bash
# Start all services
docker-compose up -d --scale worker=3

# Run migrations
docker-compose exec api python manage.py migrate

# Create superuser
docker-compose exec api python manage.py createsuperuser

# Access dashboard at http://localhost:8000/monitoring/
```

### 3. Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start infrastructure
docker-compose up -d redis postgres

# Run migrations
python manage.py migrate

# Start API server (Terminal 1)
python manage.py runserver

# Start worker (Terminal 2)
WORKER_ID=dev-worker-1 python worker/worker.py

# Access API at http://localhost:8000/api/v1/
# Access Dashboard at http://localhost:8000
```

## Configuration

### Environment Variables

```env
# Django
DEBUG=False
SECRET_KEY=secret-key-here
ALLOWED_HOSTS=localhost,api.yourdomain.com

# Database
DATABASE_URL=postgres://user:password@localhost:5432/jobqueue

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Optional

# Worker
WORKER_POLL_INTERVAL=1.0
WORKER_HEARTBEAT_TTL=30
MAX_RETRY_ATTEMPTS=3

# Rate Limiting
RATE_LIMIT_REQUESTS=100  # per minute
RATE_LIMIT_WINDOW=60
```

## API Reference

#### Submit a Job

```bash
POST /api/v1/jobs/
Content-Type: application/json
Authorization: Token <your-api-token>

{
  "task_type": "email",
  "payload": {
    "to": "user@example.com",
    "subject": "Welcome",
    "body": "Hello World!"
  },
  "priority": 2,
  "scheduled_at": "2026-04-01T10:00:00Z",
  "max_retries": 3
}
```

#### Response:
```bash
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "priority": 2,
  "created_at": "2026-03-31T19:34:00Z"
}
```

#### Check Job Status
```bash
GET /api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/
```

#### Manual Retry
```bash
POST /api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/retry/
```

#### System Statistics
```bash
GET /api/v1/jobs/stats/
```


#### Response:
```bash
{
  "redis": {
    "queued": 45,
    "processing": 3,
    "scheduled": 12,
    "dead_letter": 2
  },
  "database": {
    "completed": 1523,
    "failed": 12
  },
  "workers": {
    "active": 3,
    "idle": 1
  }
}
```

## Worker Configuration

#### Scaling Workers
```bash
# Docker Compose - Scale to 5 workers
docker-compose up -d --scale worker=5 --no-recreate

# Kubernetes (example)
kubectl scale deployment job-worker --replicas=10
```

#### Custom Task Processors
Create `worker/processors.py`
```bash
from worker.processors import BaseProcessor, TaskProcessorRegistry

class VideoProcessor(BaseProcessor):
    def execute(self, payload):
        video_url = payload['video_url']
        # Processing logic here
        return {
            'processed': True,
            'duration': 120,
            'thumbnail_url': 'https://cdn.example.com/thumb.jpg'
        }

# Register
TaskProcessorRegistry.register('video_transcode', VideoProcessor)
```
### Worker Environment Variables

| Variable             | Description                    | Default       |
| -------------------- | ------------------------------ | ------------- |
| `WORKER_ID`          | Unique worker identifier       | UUID          |
| `WORKER_CONCURRENCY` | Parallel jobs per worker       | 1             |
| `POLL_INTERVAL`      | Queue poll frequency (seconds) | 1.0           |
| `MAX_JOBS`           | Max jobs before auto-shutdown  | 0 (unlimited) |

## Monitoring Dashboard

Features
- Real-time Metrics: Auto-refreshing stats every 3 seconds
- Job Explorer: Filter by status, priority, task type
- Dead Letter Queue: Visual management of failed jobs
- Worker Status: Live heartbeat monitoring
- Performance Charts: Throughput and distribution visualization

#### Access Control
```bash
# monitoring/views.py
from django.contrib.admin.views.decorators import staff_member_required

class DashboardView(TemplateView):
    @method_decorator(staff_member_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
```

#### Prometheus Metrics
```bash
# urls.py
path('metrics/', exports.ExportToDjangoView, name='prometheus-django-metrics'),
```

#### Deployment
Production Checklist
- [ ] Change default SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configure PostgreSQL with SSL
- [ ] Enable Redis AUTH password
- [ ] Set up log rotation (structlog JSON format)
- [ ] Configure backups (Postgres daily, Redis RDB)
- [ ] Set up monitoring alerts (PagerDuty/Slack)
- [ ] Enable API throttling
- [ ] Configure CORS properly
- [ ] Use HTTPS only (SECURE_SSL_REDIRECT)

## Contributing
1. Fork the repository
1. Create feature branch (git checkout -b feature/amazing-feature)
1. Commit changes (git commit -m 'Add amazing feature')
1. Push to branch (git push origin feature/amazing-feature)
1. Open Pull Request

## License
Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

## Acknowledgments
- Django REST Framework for the excellent API toolkit
- Redis for high-performance queuing
- Tailwind CSS for the dashboard UI