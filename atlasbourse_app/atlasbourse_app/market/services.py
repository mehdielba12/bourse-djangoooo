from decimal import Decimal
from datetime import timedelta

import yfinance as yf

from django.utils import timezone
from django.db.models import Max

from .models import Stock


def fetch_stock_price(symbol: str):
    """جيب آخر ثمن من yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")

        if data.empty:
            return None

        last_close = data["Close"].iloc[-1]
        # نرجع Decimal بـ 2 أرقام بعد الفاصلة
        return Decimal(str(round(float(last_close), 2)))
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None


# شحال من دقيقة بين update و update
AUTO_UPDATE_INTERVAL_MINUTES = 1


def update_all_stock_prices():
    """
    كتـحدّث last_price ديال جميع الأسهم من الــAPI.
    updated_at غيتحدّث بوحدو (auto_now=True فـ model).
    """
    now = timezone.now()

    for stock in Stock.objects.all():
        price = fetch_stock_price(stock.symbol)
        if price is not None:
            stock.last_price = price
            stock.save(update_fields=["last_price"])

    return now


def auto_update_prices_if_needed():
    """
    إلا كان آخر update قديم (أكتر من AUTO_UPDATE_INTERVAL_MINUTES)
    كنعيطو على update_all_stock_prices.
    كترد (just_updated, last_update)
    """
    now = timezone.now()

    # آخر updated_at فـ جميع الأسهم
    last_update = Stock.objects.aggregate(last=Max("updated_at"))["last"]

    if last_update is None or last_update < now - timedelta(minutes=AUTO_UPDATE_INTERVAL_MINUTES):
        last_update = update_all_stock_prices()
        just_updated = True
    else:
        just_updated = False

    return just_updated, last_update
