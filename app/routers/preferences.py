from decimal import Decimal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ..db import SessionDep
from ..flash import flash
from ..i18n import catalog
from ..security import CurrentUser, RequiredUser
from ..services.invoicing import CURRENCIES, LANGUAGES, numeric
from ..templating import render

router = APIRouter(tags=["settings"])
FIELDS = (
    "issuer_name",
    "issuer_email",
    "issuer_address",
    "payment_instructions",
    "default_currency",
    "default_tax_rate",
    "language",
    "document_language",
)


@router.get("/settings")
def settings_form(request: Request, user: RequiredUser):
    form = {key: getattr(user, key) for key in FIELDS}
    return render(
        request,
        "settings.html",
        {"user": user, "preferences": user, "form": form, "fields": form},
    )


@router.post("/settings")
async def settings_save(request: Request, session: SessionDep, user: RequiredUser):
    raw = await request.form()
    form = {key: str(raw.get(key, getattr(user, key))).strip() for key in FIELDS}
    errors = {}
    if not form["issuer_name"]:
        errors["issuer_name"] = "Name is required."
    if form["issuer_email"] and (
        "@" not in form["issuer_email"] or " " in form["issuer_email"]
    ):
        errors["issuer_email"] = "Enter a valid email address."
    if form["default_currency"] not in CURRENCIES:
        errors["default_currency"] = "Select a supported currency."
    for key in ("language", "document_language"):
        if form[key] not in LANGUAGES:
            errors[key] = "Select a language."
    tax = numeric(
        form["default_tax_rate"],
        "default_tax_rate",
        errors,
        maximum=Decimal(100),
        places=4,
    )
    if errors:
        return render(
            request,
            "settings.html",
            {
                "user": user,
                "preferences": user,
                "form": form,
                "fields": form,
                "errors": errors,
                "error": next(iter(errors.values())),
            },
            status_code=400,
        )
    form["default_tax_rate"] = str(tax)
    for key, value in form.items():
        setattr(user, key, value)
    session.add(user)
    session.commit()
    request.session["language"] = user.language
    flash(request, "Settings saved.")
    return RedirectResponse("/settings", 303)


@router.post("/language")
async def set_language(request: Request, session: SessionDep, user: CurrentUser):
    raw = (
        await request.json()
        if "application/json" in request.headers.get("content-type", "")
        else await request.form()
    )
    language = raw.get("language", "")
    if language not in LANGUAGES:
        return JSONResponse({"error": "Select a language."}, status_code=400)
    request.session["language"] = language
    if user:
        user.language = language
        session.add(user)
        session.commit()
    return {"language": language, "strings": catalog(language)}
