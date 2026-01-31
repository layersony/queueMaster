import requests
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseProcessor(ABC):
    @abstractmethod
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

class EmailProcessor(BaseProcessor):
    def execute(self, payload):
        # Send email logic
        to = payload['to']
        subject = payload['subject']
        body = payload['body']
        
        # Integration with SendGrid/AWS SES
        # response = send_email(to, subject, body)
        
        return {'sent': True, 'recipient': to}

class ImageProcessor(BaseProcessor):
    def execute(self, payload):
        # Image processing logic
        image_url = payload['image_url']
        operations = payload.get('operations', [])
        
        # Download, process, upload to S3
        # result = process_image(image_url, operations)
        
        return {'processed': True, 'operations': len(operations)}

class TaskProcessorRegistry:
    _registry = {
        'email': EmailProcessor,
        'image_processing': ImageProcessor,
        # Add more task types
    }
    
    @classmethod
    def get(cls, task_type: str) -> BaseProcessor:
        if task_type not in cls._registry:
            raise ValueError(f"Unknown task type: {task_type}")
        return cls._registry[task_type]()
    
    @classmethod
    def register(cls, task_type: str, processor_class: Type[BaseProcessor]):
        cls._registry[task_type] = processor_class