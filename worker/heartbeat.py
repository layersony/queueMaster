class HeartbeatManager:
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.redis = JobQueue().redis_client
    
    def beat(self):
        key = f"worker:{self.worker_id}:heartbeat"
        self.redis.setex(key, 30, datetime.now().isoformat())
    
    @classmethod
    def get_active_workers(cls):
        redis = JobQueue().redis_client
        keys = redis.keys("worker:*:heartbeat")
        return [k.split(':')[1] for k in keys]