import json
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone
from products.models import Product, ProductCategory
from .models import Order, OrderItem, Shift
from .utils import broadcast_order_event, broadcast_shift_event, broadcast_category_event
from django.db.models import Sum, Count, Q
from django.conf import settings
from datetime import timedelta


def get_current_business_date():
    return timezone.localdate()


def get_open_shift(business_date=None):
    business_date = business_date or get_current_business_date()
    return (
        Shift.objects
        .filter(business_date=business_date, status=Shift.STATUS_OPEN)
        .order_by("-opened_at")
        .first()
    )


def get_next_shift_sequence(business_date=None):
    business_date = business_date or get_current_business_date()
    last_shift = (
        Shift.objects
        .filter(business_date=business_date)
        .order_by("-sequence_number")
        .first()
    )
    return 1 if not last_shift else last_shift.sequence_number + 1


def has_recent_shift_summary_verification(request):
    verified_at = request.session.get("shift_summary_verified_at")
    if not verified_at:
        return False

    try:
        verified_at = timezone.datetime.fromisoformat(verified_at)
    except (TypeError, ValueError):
        return False

    if timezone.is_naive(verified_at):
        verified_at = timezone.make_aware(verified_at, timezone.get_current_timezone())

    return timezone.now() <= verified_at + timedelta(seconds=settings.SHIFT_SUMMARY_PIN_TTL_SECONDS)


def mark_shift_summary_verified(request):
    request.session["shift_summary_verified_at"] = timezone.now().isoformat()
    request.session.modified = True


def user_in_group(user, group_name):
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


def can_access_live(user):
    return user.is_authenticated and (
        user.is_superuser
        or user_in_group(user, "Bar")
        or user_in_group(user, "Managers")
    )


def can_access_shift_summary(user):
    return user.is_authenticated and (
        user.is_superuser
        or user_in_group(user, "Managers")
    )


def can_open_close_shift(user):
    return user.is_authenticated and (
        user.is_superuser
        or user_in_group(user, "Bar")
        or user_in_group(user, "Managers")
    )


def can_submit_orders(user):
    return user.is_authenticated and (
        user.is_superuser
        or user_in_group(user, "Waiters")
        or user_in_group(user, "Managers")
    )


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


def serialize_category(category, include_products=False):
    data = {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "is_active": category.is_active,
        "show_on_live_controls": category.show_on_live_controls,
        "sort_order": category.sort_order,
    }

    if include_products:
        products = (
            category.products
            .filter(is_active=True)
            .order_by("name")
            .values("id", "name", "price")
        )
        data["products"] = [
            {
                "id": product["id"],
                "name": product["name"],
                "price": str(product["price"]),
            }
            for product in products
        ]

    return data


@login_required
def home(request):
    return render(request, "orders/home.html", {
        "open_shift": get_open_shift(),
        "business_date": get_current_business_date(),
        "can_access_live": can_access_live(request.user),
        "can_access_shift_summary": can_access_shift_summary(request.user),
        "can_submit_orders": can_submit_orders(request.user),
    })


@user_passes_test(can_submit_orders, login_url="login")
def waiter_order_page(request):
    products = (
        Product.objects
        .filter(is_active=True, category__is_active=True)
        .select_related("category")
        .order_by("category__sort_order", "category__name", "name")
    )
    open_shift = get_open_shift()

    return render(request, "orders/waiter_order_page.html", {
        "products": products,
        "open_shift": open_shift,
        "business_date": get_current_business_date(),
        "can_access_live": can_access_live(request.user),
        "can_access_shift_summary": can_access_shift_summary(request.user),
    })


@user_passes_test(can_access_live, login_url="login")
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

    categories = ProductCategory.objects.filter(
        show_on_live_controls=True
    ).order_by("sort_order", "name")

    grouped_pending = {}
    for order in pending_orders:
        waiter_name = order.waiter.get_full_name() or order.waiter.username
        grouped_pending.setdefault(waiter_name, []).append(order)

    return render(request, "orders/live_orders_page.html", {
        "grouped_pending": grouped_pending,
        "recent_finished_orders": recent_finished_orders,
        "categories": categories,
        "open_shift": get_open_shift(),
        "business_date": get_current_business_date(),
        "can_access_shift_summary": can_access_shift_summary(request.user),
        "can_open_close_shift": can_open_close_shift(request.user),
        "can_submit_orders": can_submit_orders(request.user)
    })


@user_passes_test(can_access_live, login_url="login")
@require_POST
def set_category_active(request, category_id):
    category = get_object_or_404(ProductCategory, id=category_id)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON body."}, status=400)

    is_active = data.get("is_active")

    if not isinstance(is_active, bool):
        return JsonResponse(
            {"success": False, "error": "Field 'is_active' must be true or false."},
            status=400,
        )

    if category.is_active == is_active:
        return JsonResponse({
            "success": True,
            "message": f"Category '{category.name}' already {'active' if category.is_active else 'inactive'}.",
            "category": serialize_category(category, include_products=True),
        })

    category.is_active = is_active
    category.save(update_fields=["is_active"])

    category_payload = serialize_category(category, include_products=True)

    broadcast_category_event({
        "event": "category_updated",
        "category": category_payload,
    })

    return JsonResponse({
        "success": True,
        "message": f"Category '{category.name}' {'enabled' if category.is_active else 'disabled'}.",
        "category": category_payload,
    })


@user_passes_test(can_submit_orders, login_url="login")
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

    shift = get_open_shift()

    if not shift:
        return JsonResponse(
            {"success": False, "error": "No open shift. New orders are currently blocked."},
            status=400
        )

    order = Order.objects.create(
        waiter=request.user,
        shift=shift,
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
            product = Product.objects.select_related("category").get(
                id=product_id,
                is_active=True,
                category__is_active=True,
            )
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


@user_passes_test(can_access_live, login_url="login")
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


@user_passes_test(can_access_live, login_url="login")
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


@user_passes_test(can_open_close_shift, login_url="login")
@require_POST
def open_shift(request):
    business_date = get_current_business_date()
    existing_open = get_open_shift(business_date)

    if existing_open:
        return JsonResponse(
            {"success": False, "error": "There is already an open shift for today."},
            status=400
        )

    shift = Shift.objects.create(
        business_date=business_date,
        sequence_number=get_next_shift_sequence(business_date),
        status=Shift.STATUS_OPEN,
        opened_by=request.user,
    )

    broadcast_shift_event({
        "event": "shift_updated",
        "shift": {
            "id": shift.id,
            "business_date": str(shift.business_date),
            "sequence_number": shift.sequence_number,
            "status": shift.status,
            "opened_at": shift.opened_at.strftime("%Y-%m-%d %H:%M:%S") if shift.opened_at else "",
            "closed_at": "",
            "opened_by": shift.opened_by.get_full_name() or shift.opened_by.username if shift.opened_by else "",
            "closed_by": "",
        }
    })

    return JsonResponse({
        "success": True,
        "message": f"Opened Shift {shift.sequence_number} for {shift.business_date}.",
        "shift_id": shift.id,
        "sequence_number": shift.sequence_number,
        "business_date": str(shift.business_date),
    })


@user_passes_test(can_access_shift_summary, login_url="login")
def shift_summary_page(request):
    if not has_recent_shift_summary_verification(request):
        return redirect("shift_summary_unlock")

    business_date = get_current_business_date()
    open_shift = get_open_shift(business_date)

    shifts_for_day = (
        Shift.objects
        .filter(business_date=business_date)
        .select_related("opened_by", "closed_by")
        .order_by("sequence_number")
    )

    shift_summaries = []

    for shift in shifts_for_day:
        shift_orders = Order.objects.filter(shift=shift)

        shift_totals = shift_orders.aggregate(
            total_orders=Count("id"),
            pending_orders=Count("id", filter=Q(status=Order.STATUS_PENDING)),
            finished_orders=Count("id", filter=Q(status=Order.STATUS_FINISHED)),
            canceled_orders=Count("id", filter=Q(status=Order.STATUS_CANCELED)),
            total_amount=Sum("total"),
            finished_amount=Sum("total", filter=Q(status=Order.STATUS_FINISHED)),
            canceled_amount=Sum("total", filter=Q(status=Order.STATUS_CANCELED)),
        )

        waiter_totals = (
            shift_orders
            .select_related("waiter")
            .values("waiter__username", "waiter__first_name", "waiter__last_name")
            .annotate(
                total_orders=Count("id"),
                pending_orders=Count("id", filter=Q(status=Order.STATUS_PENDING)),
                finished_orders=Count("id", filter=Q(status=Order.STATUS_FINISHED)),
                canceled_orders=Count("id", filter=Q(status=Order.STATUS_CANCELED)),
                total_amount=Sum("total"),
                finished_amount=Sum("total", filter=Q(status=Order.STATUS_FINISHED)),
                canceled_amount=Sum("total", filter=Q(status=Order.STATUS_CANCELED)),
            )
            .order_by("waiter__username")
        )

        shift_summaries.append({
            "shift": shift,
            "totals": shift_totals,
            "waiter_totals": waiter_totals,
        })

    overall = Order.objects.filter(shift__business_date=business_date).aggregate(
        total_orders=Count("id"),
        pending_orders=Count("id", filter=Q(status=Order.STATUS_PENDING)),
        finished_orders=Count("id", filter=Q(status=Order.STATUS_FINISHED)),
        canceled_orders=Count("id", filter=Q(status=Order.STATUS_CANCELED)),
        total_amount=Sum("total"),
        finished_amount=Sum("total", filter=Q(status=Order.STATUS_FINISHED)),
        canceled_amount=Sum("total", filter=Q(status=Order.STATUS_CANCELED)),
    )

    return render(request, "orders/shift_summary.html", {
        "business_date": business_date,
        "open_shift": open_shift,
        "shift_summaries": shift_summaries,
        "overall": overall,
        "can_open_close_shift": can_open_close_shift(request.user),
        "can_submit_orders": can_submit_orders(request.user),
    })


@user_passes_test(can_open_close_shift, login_url="login")
@require_POST
def close_shift(request):
    shift = get_open_shift()

    if not shift:
        return JsonResponse({"success": False, "error": "No open shift to close."}, status=400)

    shift.status = Shift.STATUS_CLOSED
    shift.closed_at = timezone.now()
    shift.closed_by = request.user
    shift.save(update_fields=["status", "closed_at", "closed_by"])

    broadcast_shift_event({
        "event": "shift_updated",
        "shift": {
            "id": shift.id,
            "business_date": str(shift.business_date),
            "sequence_number": shift.sequence_number,
            "status": shift.status,
            "opened_at": shift.opened_at.strftime("%Y-%m-%d %H:%M:%S") if shift.opened_at else "",
            "closed_at": shift.closed_at.strftime("%Y-%m-%d %H:%M:%S") if shift.closed_at else "",
            "opened_by": shift.opened_by.get_full_name() or shift.opened_by.username if shift.opened_by else "",
            "closed_by": shift.closed_by.get_full_name() or shift.closed_by.username if shift.closed_by else "",
        }
    })

    return JsonResponse({
        "success": True,
        "message": f"Closed Shift {shift.sequence_number} for {shift.business_date}.",
        "shift_id": shift.id,
        "sequence_number": shift.sequence_number,
        "business_date": str(shift.business_date),
    })


@user_passes_test(can_access_shift_summary, login_url="login")
def shift_summary_unlock(request):
    if has_recent_shift_summary_verification(request):
        return redirect("shift_summary_page")

    error = None

    if request.method == "POST":
        entered_pin = (request.POST.get("pin") or "").strip()

        if entered_pin == settings.SHIFT_SUMMARY_PIN:
            mark_shift_summary_verified(request)
            return redirect("shift_summary_page")

        error = "Invalid passcode."

    return render(request, "orders/shift_summary_unlock.html", {
        "error": error,
        "can_access_live": can_access_live(request.user),
    })

