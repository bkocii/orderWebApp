from django.db import models


class Product(models.Model):
    CATEGORY_CHOICES = [
        ("soft", "Soft Drinks"),
        ("coffee", "Coffee"),
        ("beer", "Beer"),
        ("cocktail", "Cocktail"),
        ("water", "Water"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="other")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.price})"