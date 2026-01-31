import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("dashboard_updates", self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("dashboard_updates", self.channel_name)
    
    async def receive(self, text_data):
        # Handle client pings
        await self.send(text_data=json.dumps({'type': 'pong'}))
    
    async def stats_update(self, event):
        # Broadcast stats to all connected clients
        await self.send(text_data=json.dumps({
            'type': 'stats',
            'data': event['data']
        }))

# In your worker, add:
# channel_layer.group_send("dashboard_updates", {"type": "stats.update", "data": {...}})