from django.db import models
from django.contrib.auth.models import User


class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    last_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default="USD")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.symbol} - {self.name}"


class Portfolio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cash = models.DecimalField(max_digits=12, decimal_places=2, default=10000)

    def __str__(self):
        return f"Portefeuille de {self.user.username}"


class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="positions")
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    avg_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("portfolio", "stock")

    def __str__(self):
        return f"{self.portfolio.user.username} - {self.stock.symbol}"


class Transaction(models.Model):
    BUY = "BUY"
    SELL = "SELL"
    TYPE_CHOICES = [
        (BUY, "Achat"),
        (SELL, "Vente"),
    ]

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="transactions")
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    type = models.CharField(max_length=4, choices=TYPE_CHOICES)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} {self.quantity} {self.stock.symbol} à {self.price}"


class CashOperation(models.Model):
    IN = "IN"
    OUT = "OUT"
    TYPE_CHOICES = [
        (IN, "Dépôt"),
        (OUT, "Retrait"),
    ]

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="cash_operations")
    type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        signe = "+" if self.type == self.IN else "-"
        return f"{signe}{self.amount} sur {self.portfolio.user.username}"
