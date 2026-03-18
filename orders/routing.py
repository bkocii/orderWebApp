from django.urls import path

from .consumers import LiveOrdersConsumer

websocket_urlpatterns = [
    path("ws/orders/live/", LiveOrdersConsumer.as_asgi()),
]