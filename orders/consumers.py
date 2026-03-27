import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class LiveOrdersConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close()
            return

        self.group_names = ["shift_updates"]

        if await self.has_live_access(user):
            self.group_names.append("live_orders_staff")

        for group_name in self.group_names:
            await self.channel_layer.group_add(group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_names"):
            for group_name in self.group_names:
                await self.channel_layer.group_discard(group_name, self.channel_name)

    async def order_event(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    @database_sync_to_async
    def has_live_access(self, user):
        return (
            user.is_superuser
            or user.groups.filter(name__in=["Bar", "Managers"]).exists()
        )