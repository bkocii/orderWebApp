from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from products.models import Product


@login_required
def home(request):
    return render(request, "orders/home.html")


@login_required
def waiter_order_page(request):
    products = Product.objects.filter(is_active=True).order_by("category", "name")
    return render(request, "orders/waiter_order_page.html", {"products": products})


@login_required
def live_orders_page(request):
    return render(request, "orders/live_orders_page.html")