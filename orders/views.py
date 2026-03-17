import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
from products.models import Product
from .models import Order, OrderItem


@login_required
def home(request):
    return render(request, "orders/home.html")


@login_required
def waiter_order_page(request):
    products = Product.objects.filter(is_active=True).order_by("category", "name")
    return render(request, "orders/waiter_order_page.html", {"products": products})


@staff_member_required(login_url="login")
def live_orders_page(request):
    pending_orders = (
        Order.objects
        .filter(status=Order.STATUS_PENDING)
        .select_related("waiter")
        .prefetch_related("items__product")
        .order_by("created_at")
    )
    return render(request, "orders/live_orders_page.html", {"pending_orders": pending_orders})


@login_required
@require_POST
def submit_order(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON body."}, status=400)

    table_number = (data.get("table_number") or "").strip()
    note = (data.get("note") or "").strip()
    items = data.get("items") or []

    if not items:
        return JsonResponse({"success": False, "error": "No items selected."}, status=400)

    order = Order.objects.create(
        waiter=request.user,
        table_number=table_number,
        note=note,
    )

    created_any = False

    for row in items:
        product_id = row.get("product_id")
        quantity = row.get("quantity", 1)

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = 0

        if not product_id or quantity <= 0:
            continue

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            continue

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
        )
        created_any = True

    if not created_any:
        order.delete()
        return JsonResponse({"success": False, "error": "No valid items to save."}, status=400)

    order.recalculate_total()

    return JsonResponse({
        "success": True,
        "message": "Order created successfully.",
        "order_id": order.id,
        "total": str(order.total),
    })


@staff_member_required(login_url="login")
@require_POST
def finish_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status != Order.STATUS_PENDING:
        return JsonResponse({"success": False, "error": "Order already processed."}, status=400)

    order.status = Order.STATUS_FINISHED
    order.finished_at = timezone.now()
    order.save(update_fields=["status", "finished_at", "updated_at"])

    return JsonResponse({
        "success": True,
        "order_id": order.id,
        "new_status": order.status,
    })


@staff_member_required(login_url="login")
@require_POST
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status != Order.STATUS_PENDING:
        return JsonResponse({"success": False, "error": "Order already processed."}, status=400)

    order.status = Order.STATUS_CANCELED
    order.canceled_at = timezone.now()
    order.save(update_fields=["status", "canceled_at", "updated_at"])

    return JsonResponse({
        "success": True,
        "order_id": order.id,
        "new_status": order.status,
    })

