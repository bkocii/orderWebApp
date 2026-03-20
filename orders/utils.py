from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_to_group(group_name, data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "order_event",
            "data": data,
        },
    )


def broadcast_order_event(data):
    broadcast_to_group("live_orders_staff", data)


def broadcast_shift_event(data):
    broadcast_to_group("shift_updates", data)


def broadcast_category_event(data):
    broadcast_to_group("shift_updates", data)
    broadcast_to_group("live_orders_staff", data)
