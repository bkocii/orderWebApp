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
from .utils import broadcast_order_event


def serialize_order(order):
    return {
        "id": order.id,
        "waiter": order.waiter.get_full_name() or order.waiter.username,
        "table_number": order.table_number or "",
        "note": order.note or "",
        "status": order.status,
        "created_at": order.created_at.strftime("%H:%M:%S") if order.created_at else "",
        "finished_at": order.finished_at.strftime("%H:%M:%S") if order.finished_at else "",
        "canceled_at": order.canceled_at.strftime("%H:%M:%S") if order.canceled_at else "",
        "total": str(order.total),
        "items": [
            {
                "name": item.product.name,
                "quantity": item.quantity,
                "subtotal": str(item.subtotal),
            }
            for item in order.items.select_related("product").all()
        ],
    }


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

    recent_finished_orders = (
        Order.objects
        .filter(status=Order.STATUS_FINISHED)
        .select_related("waiter")
        .prefetch_related("items__product")
        .order_by("-finished_at")[:5]
    )

    grouped_pending = {}
    for order in pending_orders:
        waiter_name = order.waiter.get_full_name() or order.waiter.username
        grouped_pending.setdefault(waiter_name, []).append(order)

    return render(request, "orders/live_orders_page.html", {
        "grouped_pending": grouped_pending,
        "recent_finished_orders": recent_finished_orders,
    })


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
    order.refresh_from_db()

    broadcast_order_event({
        "event": "order_created",
        "order": serialize_order(order),
    })

    return JsonResponse({
        "success": True,
        "message": "Order created successfully.",
        "order_id": order.id,
        "total": str(order.total),
    })


@staff_member_required(login_url="login")
@require_POST
def finish_order(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("waiter").prefetch_related("items__product"),
        id=order_id
    )

    if order.status != Order.STATUS_PENDING:
        return JsonResponse({"success": False, "error": "Order already processed."}, status=400)

    order.status = Order.STATUS_FINISHED
    order.finished_at = timezone.now()
    order.save(update_fields=["status", "finished_at", "updated_at"])
    order.refresh_from_db()

    broadcast_order_event({
        "event": "order_updated",
        "order": serialize_order(order),
    })

    return JsonResponse({
        "success": True,
        "order_id": order.id,
        "new_status": order.status,
        "order": serialize_order(order),
    })


@staff_member_required(login_url="login")
@require_POST
def cancel_order(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("waiter").prefetch_related("items__product"),
        id=order_id
    )

    if order.status != Order.STATUS_PENDING:
        return JsonResponse({"success": False, "error": "Order already processed."}, status=400)

    order.status = Order.STATUS_CANCELED
    order.canceled_at = timezone.now()
    order.save(update_fields=["status", "canceled_at", "updated_at"])
    order.refresh_from_db()

    broadcast_order_event({
        "event": "order_updated",
        "order": serialize_order(order),
    })

    return JsonResponse({
        "success": True,
        "order_id": order.id,
        "new_status": order.status,
        "order": serialize_order(order),
    })

