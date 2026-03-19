from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.db import models

from products.models import Product


class Shift(models.Model):
    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_CLOSED, "Closed"),
    ]

    business_date = models.DateField(default=timezone.localdate)
    sequence_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(blank=True, null=True)

    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opened_shifts",
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_shifts",
    )

    class Meta:
        ordering = ["-business_date", "-opened_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["business_date", "sequence_number"],
                name="unique_shift_sequence_per_day",
            )
        ]

    def __str__(self):
        return f"{self.business_date} / Shift {self.sequence_number} ({self.status})"


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_FINISHED = "finished"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_FINISHED, "Finished"),
        (STATUS_CANCELED, "Canceled"),
    ]

    waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    table_number = models.CharField(max_length=20, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    canceled_at = models.DateTimeField(blank=True, null=True)
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="orders", null=True, blank=True, )
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - {self.waiter}"

    def recalculate_total(self):
        total = sum((item.subtotal for item in self.items.all()), Decimal("0.00"))
        self.total = total
        self.save(update_fields=["total"])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name = "Order item"
        verbose_name_plural = "Order items"

    def save(self, *args, **kwargs):
        self.unit_price = self.product.price
        self.subtotal = Decimal(self.quantity) * self.unit_price
        super().save(*args, **kwargs)
        self.order.recalculate_total()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.recalculate_total()

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
