from django.contrib import admin
from .models import Stock, Portfolio, Position, Transaction, CashOperation

admin.site.register(Stock)
admin.site.register(Portfolio)
admin.site.register(Position)
admin.site.register(Transaction)
admin.site.register(CashOperation)
