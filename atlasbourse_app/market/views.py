import json
from django.utils.safestring import mark_safe

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.db.models import Q


from .forms import RegisterForm, OrderForm, CashOperationForm, SymbolSearchForm
from .models import Stock, Portfolio, Position, Transaction, CashOperation
from .services import fetch_stock_price
from .services import auto_update_prices_if_needed




def get_user_portfolio(user):
    portfolio, _ = Portfolio.objects.get_or_create(user=user)
    return portfolio


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Portfolio.objects.create(user=user)
            login(request, user)
            messages.success(request, "Compte créé avec succès !")
            return redirect("dashboard")
    else:
        form = RegisterForm()

    return render(request, "registration/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Connexion réussie.")
            return redirect("dashboard")
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    else:
        form = AuthenticationForm()

    return render(request, "registration/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect("login")


def compute_portfolio_totals(portfolio):
    """
    Kat7seb:
      - valeur totale des positions
      - valeur totale portefeuille
      - gain/perte global
      W kat3mr 3la kol position:
        pos.gain        -> gain/perte en montant
        pos.gain_percent -> gain/perte en %
    """
    positions = portfolio.positions.select_related("stock")
    total_positions_value = Decimal("0")
    total_gain = Decimal("0")

    for pos in positions:
        last_price = pos.stock.last_price or pos.avg_price or Decimal("0")
        avg_price = pos.avg_price or Decimal("0")

        position_value = last_price * pos.quantity
        total_positions_value += position_value

        gain = (last_price - avg_price) * pos.quantity
        pos.gain = gain

        if avg_price > 0:
            pos.gain_percent = (last_price - avg_price) / avg_price * Decimal("100")
        else:
            pos.gain_percent = Decimal("0")

        total_gain += gain

    total_value = portfolio.cash + total_positions_value
    return positions, total_positions_value, total_value, total_gain


@login_required
def dashboard(request):
    # 1) stock jay men bouton "Trader" (param ?symbol=)
    symbol = request.GET.get("symbol")
    selected_stock = None
    if symbol:
        selected_stock = Stock.objects.filter(symbol__iexact=symbol).first()

    # 2) données du portefeuille
    portfolio = get_user_portfolio(request.user)
    (
        positions,
        total_positions_value,
        total_value,
        total_gain,
    ) = compute_portfolio_totals(portfolio)

    # 3) formulaire ordre : n3amro symbol ila ja men Trader
    if symbol:
        form = OrderForm(initial={"symbol": symbol})
    else:
        form = OrderForm()

    # 4) data dyal chart
    labels = []
    values = []
    for pos in positions:
        last_price = pos.stock.last_price or pos.avg_price or Decimal("0")
        labels.append(pos.stock.symbol)
        values.append(float(last_price * pos.quantity))

    chart_data = {"labels": labels, "values": values}

    context = {
        "portfolio": portfolio,
        "positions": positions,
        "total_positions_value": total_positions_value,
        "total_value": total_value,
        "total_gain": total_gain,
        "form": form,
        "chart_data_json": mark_safe(json.dumps(chart_data)),
        "selected_stock": selected_stock,  # hadik li kay9raha template
    }
    return render(request, "market/dashboard.html", context)


@login_required
def place_order(request):
    portfolio = get_user_portfolio(request.user)

    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            symbol = form.cleaned_data["symbol"].upper()
            order_type = form.cleaned_data["type"]
            quantity = form.cleaned_data["quantity"]

            try:
                stock = Stock.objects.get(symbol=symbol)
            except Stock.DoesNotExist:
                messages.error(request, "Ce symbole n'existe pas dans les Stocks (ajoutez-le depuis l'admin).")
                return redirect("dashboard")

            new_price = fetch_stock_price(symbol)
            if new_price is not None:
                stock.last_price = new_price
                stock.save()
                messages.info(request, f"Prix mis à jour depuis l'API externe: {new_price}")
            else:
                messages.warning(
                    request,
                    "Impossible de récupérer le prix en ligne; on utilise le prix configuré dans l'admin.",
                )

            if stock.last_price is None:
                messages.error(request, "Aucun prix disponible pour ce symbole.")
                return redirect("dashboard")

            price = stock.last_price
            total_amount = price * quantity

            if order_type == "BUY":
                if portfolio.cash < total_amount:
                    messages.error(request, "Solde insuffisant pour cet achat.")
                    return redirect("dashboard")

                portfolio.cash -= total_amount
                portfolio.save()

                position, created = Position.objects.get_or_create(
                    portfolio=portfolio,
                    stock=stock,
                    defaults={"quantity": quantity, "avg_price": price},
                )
                if not created:
                    old_total = position.avg_price * position.quantity
                    new_total = old_total + total_amount
                    new_qty = position.quantity + quantity
                    position.avg_price = new_total / new_qty
                    position.quantity = new_qty
                    position.save()

                Transaction.objects.create(
                    portfolio=portfolio,
                    stock=stock,
                    type=Transaction.BUY,
                    quantity=quantity,
                    price=price,
                )
                messages.success(request, f"Achat de {quantity} {symbol} effectué.")
            else:  # SELL
                try:
                    position = Position.objects.get(portfolio=portfolio, stock=stock)
                except Position.DoesNotExist:
                    messages.error(request, "Vous ne détenez pas cette action.")
                    return redirect("dashboard")

                if position.quantity < quantity:
                    messages.error(request, "Quantité à vendre trop élevée.")
                    return redirect("dashboard")

                position.quantity -= quantity
                if position.quantity == 0:
                    position.delete()
                else:
                    position.save()

                portfolio.cash += total_amount
                portfolio.save()

                Transaction.objects.create(
                    portfolio=portfolio,
                    stock=stock,
                    type=Transaction.SELL,
                    quantity=quantity,
                    price=price,
                )
                messages.success(request, f"Vente de {quantity} {symbol} effectuée.")

            return redirect("dashboard")
    else:
        form = OrderForm()

    positions, total_positions_value, total_value, total_gain = compute_portfolio_totals(portfolio)

    return render(
        request,
        "market/dashboard.html",
        {
            "portfolio": portfolio,
            "positions": positions,
            "total_positions_value": total_positions_value,
            "total_value": total_value,
            "total_gain": total_gain,
            "form": form,
        },
    )


@login_required
def transaction_list(request):
    portfolio = get_user_portfolio(request.user)
    transactions = portfolio.transactions.select_related("stock").order_by("-created_at")
    return render(request, "market/transactions.html", {"transactions": transactions})



@login_required
def stock_list(request):
    """
    Page Marché :
    - auto-update des prix via yfinance
    - recherche + filtre par devise
    - top actions
    """

    # 1) Auto-update des prix si besoin
    just_updated, last_update = auto_update_prices_if_needed()

    # 2) queryset de base
    all_stocks = Stock.objects.all().order_by("symbol")

    # 3) Recherche / filtre
    q = request.GET.get("q", "").strip()
    currency = request.GET.get("currency", "").strip()

    stocks = all_stocks

    if q:
        stocks = stocks.filter(
            Q(symbol__icontains=q) |
            Q(name__icontains=q)
        )

    if currency:
        stocks = stocks.filter(currency__iexact=currency)

    # 4) Devises DISTINCT pour le select (هنا التعديل المهم)
    currencies = (
        Stock.objects
        .exclude(currency__isnull=True)
        .exclude(currency__exact="")
        .values_list("currency", flat=True)
        .distinct()
        .order_by("currency")
    )

    # 5) Top actions (لي عندهم ثمن و مرتّبين تنازلياً)
    top_stocks = stocks.exclude(
        last_price__isnull=True
    ).order_by("-last_price")[:5]

    context = {
        "stocks": stocks,
        "q": q,
        "currency": currency,
        "currencies": currencies,
        "top_stocks": top_stocks,
        "last_price_update": last_update,
        "just_updated": just_updated,
    }

    return render(request, "market/stocks.html", context)


@login_required
def cash_operation(request):
    portfolio = get_user_portfolio(request.user)

    if request.method == "POST":
        form = CashOperationForm(request.POST)
        if form.is_valid():
            type_op = form.cleaned_data["type"]
            amount = form.cleaned_data["amount"]
            note = form.cleaned_data["note"]

            if type_op == "IN":
                portfolio.cash += amount
                portfolio.save()
                CashOperation.objects.create(
                    portfolio=portfolio,
                    type=CashOperation.IN,
                    amount=amount,
                    note=note,
                )
                messages.success(request, f"Dépôt de {amount} MAD effectué.")
            else:
                if portfolio.cash < amount:
                    messages.error(request, "Solde insuffisant pour ce retrait.")
                    return redirect("cash_operation")

                portfolio.cash -= amount
                portfolio.save()
                CashOperation.objects.create(
                    portfolio=portfolio,
                    type=CashOperation.OUT,
                    amount=amount,
                    note=note,
                )
                messages.success(request, f"Retrait de {amount} MAD effectué.")

            return redirect("cash_operation")
    else:
        form = CashOperationForm()

    operations = portfolio.cash_operations.order_by("-created_at")[:20]

    return render(
        request,
        "market/cash.html",
        {"portfolio": portfolio, "form": form, "operations": operations},
    )
