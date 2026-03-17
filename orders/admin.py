from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "waiter", "table_number", "status", "total", "created_at")
    list_filter = ("status", "created_at", "waiter")
    search_fields = ("id", "waiter__username", "table_number", "note")
    readonly_fields = ("created_at", "updated_at", "finished_at", "canceled_at", "total")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "unit_price", "subtotal")
    list_filter = ("product",)
    search_fields = ("order__id", "product__name")
