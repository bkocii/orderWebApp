from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_order_event(data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "live_orders",
        {
            "type": "order_event",
            "data": data,
        },
    )