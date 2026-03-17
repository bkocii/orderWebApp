from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("waiter/", views.waiter_order_page, name="waiter_order_page"),
    path("live/", views.live_orders_page, name="live_orders_page"),
    path("submit-order/", views.submit_order, name="submit_order"),
]