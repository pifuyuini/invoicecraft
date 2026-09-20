from fastapi.templating import Jinja2Templates

from .config import settings

CURRENCIES = ["USD", "EUR", "GBP", "CNY", "JPY"]
_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "CNY": "¥", "JPY": "¥"}


def money(value: float, currency: str = "USD") -> str:
    symbol = _SYMBOLS.get(currency, f"{currency} ")
    return f"{symbol}{value:,.2f}"


templates = Jinja2Templates(directory="app/templates")
templates.env.filters["money"] = money
templates.env.globals["app_name"] = settings.app_name
templates.env.globals["currencies"] = CURRENCIES
