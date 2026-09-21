from fastapi import Request
from fastapi.templating import Jinja2Templates

from .config import settings
from .flash import pop_flashes

CURRENCIES = ["USD", "EUR", "GBP", "CNY", "JPY"]
_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "CNY": "¥", "JPY": "¥"}


def money(value: float, currency: str = "USD") -> str:
    symbol = _SYMBOLS.get(currency, f"{currency} ")
    return f"{symbol}{value:,.2f}"


templates = Jinja2Templates(directory="app/templates")
templates.env.filters["money"] = money
templates.env.globals["app_name"] = settings.app_name
templates.env.globals["currencies"] = CURRENCIES


def render(request: Request, name: str, context: dict | None = None, status_code: int = 200):
    ctx = dict(context or {})
    ctx.setdefault("flashes", pop_flashes(request))
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)
