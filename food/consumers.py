import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync
from rest_framework.renderers import JSONRenderer
from .models import Order
from .serializers import OrderSerializer


class ActiveOrdersConsumer(AsyncWebsocketConsumer):
    GROUP_NAME = "active_orders"

    async def connect(self):
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()
        # Send initial active orders list upon connection
        initial_data = await self.get_active_orders_payload(event_type="connection_established")
        await self.send(text_data=JSONRenderer().render(initial_data).decode('utf-8'))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Client can request fresh orders list by sending {"action": "fetch"}
        if text_data:
            try:
                data = json.loads(text_data)
                if data.get("action") == "fetch":
                    payload = await self.get_active_orders_payload(event_type="fetch")
                    await self.send(text_data=JSONRenderer().render(payload).decode('utf-8'))
            except Exception:
                pass

    async def active_orders_update(self, event):
        """Handler for events sent to the 'active_orders' group."""
        await self.send(text_data=JSONRenderer().render(event["data"]).decode('utf-8'))

    @database_sync_to_async
    def get_active_orders_payload(self, event_type="update", order_data=None):
        orders = Order.objects.filter(is_deleted=False, is_paid=False).order_by('-placed_at')
        serializer = OrderSerializer(orders, many=True)
        return {
            "type": "active_orders_update",
            "event": event_type,
            "order": order_data,
            "active_orders": serializer.data
        }


def broadcast_active_orders(event_type="update", order_data=None):
    """
    Synchronous helper function to broadcast updated active orders to all WebSocket subscribers.
    Can be called directly from REST views.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    orders = Order.objects.filter(is_deleted=False, is_paid=False).order_by('-placed_at')
    serializer = OrderSerializer(orders, many=True)
    payload = {
        "type": "active_orders_update",
        "event": event_type,
        "order": order_data,
        "active_orders": serializer.data
    }

    async_to_sync(channel_layer.group_send)(
        ActiveOrdersConsumer.GROUP_NAME,
        {
            "type": "active_orders_update",
            "data": payload
        }
    )
