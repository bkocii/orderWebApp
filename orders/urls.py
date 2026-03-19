from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("waiter/", views.waiter_order_page, name="waiter_order_page"),
    path("live/", views.live_orders_page, name="live_orders_page"),
    path("submit-order/", views.submit_order, name="submit_order"),
    path("orders/<int:order_id>/finish/", views.finish_order, name="finish_order"),
    path("orders/<int:order_id>/cancel/", views.cancel_order, name="cancel_order"),
    path("shift-summary/", views.shift_summary_page, name="shift_summary_page"),
    path("open-shift/", views.open_shift, name="open_shift"),
    path("close-shift/", views.close_shift, name="close_shift"),
]