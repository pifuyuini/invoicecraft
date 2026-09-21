from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ..config import settings
from ..security import CurrentUser
from ..templating import render

router = APIRouter(tags=["pages"])


@router.get("/")
def landing(request: Request, user: CurrentUser):
    if user:
        return RedirectResponse("/dashboard", 303)
    return render(request, "landing.html", {"free_limit": settings.free_invoice_limit})


@router.get("/pricing")
def pricing(request: Request, user: CurrentUser):
    return render(
        request,
        "pricing.html",
        {"stripe_configured": settings.stripe_configured, "user": user},
    )


@router.get("/terms")
def terms(request: Request, user: CurrentUser):
    return render(request, "terms.html", {"user": user})


@router.get("/privacy")
def privacy(request: Request, user: CurrentUser):
    return render(request, "privacy.html", {"user": user})
