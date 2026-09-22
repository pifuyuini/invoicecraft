from decimal import ROUND_HALF_UP, Decimal
from functools import partial
from urllib.parse import urlencode

from fastapi import Request
from fastapi.templating import Jinja2Templates

from .config import settings
from .flash import pop_flashes
from .i18n import catalog, translate
from .models import precision
from .services.invoicing import CURRENCIES, is_overdue

_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "CNY": "¥", "JPY": "¥"}


def money(value, currency: str = "USD") -> str:
    amount = Decimal(str(value)).quantize(precision(currency), rounding=ROUND_HALF_UP)
    return (
        f"{_SYMBOLS.get(currency, currency + ' ')}{amount:,.0f}"
        if currency == "JPY"
        else f"{_SYMBOLS.get(currency, currency + ' ')}{amount:,.2f}"
    )


templates = Jinja2Templates(directory="app/templates")
templates.env.filters["money"] = money
templates.env.globals.update(
    app_name=settings.app_name,
    currencies=CURRENCIES,
    settings=settings,
    translate=translate,
    is_overdue=is_overdue,
    urlencode=urlencode,
)


def template_context(request: Request, context=None, consume_flashes=True):
    ctx = dict(context or {})
    user = ctx.get("user")
    lang = ctx.get("lang") or (
        user.language if user else request.session.get("language", "zh-CN")
    )
    ctx.update(
        request=request,
        lang=lang,
        t=partial(translate, lang=lang),
        ui_strings=catalog(lang),
    )
    ctx.setdefault("user", None)
    ctx.setdefault("prefs", user)
    ctx.setdefault("errors", {})
    ctx.setdefault("error", None)
    if consume_flashes:
        ctx.setdefault(
            "flashes",
            [
                (kind, translate(message, lang))
                for kind, message in pop_flashes(request)
            ],
        )
    return ctx


def render(
    request: Request, name: str, context: dict | None = None, status_code: int = 200
):
    return templates.TemplateResponse(
        request, name, template_context(request, context), status_code=status_code
    )
