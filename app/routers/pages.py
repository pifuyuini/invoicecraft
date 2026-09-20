from fastapi import APIRouter, Request

from ..config import settings
from ..security import CurrentUser
from ..templating import templates

router = APIRouter(tags=["pages"])


@router.get("/")
def landing(request: Request, user: CurrentUser):
    if user:
        from fastapi.responses import RedirectResponse

        return RedirectResponse("/dashboard", 303)
    return templates.TemplateResponse(request, "landing.html", {})


@router.get("/pricing")
def pricing(request: Request, user: CurrentUser):
    return templates.TemplateResponse(
        request,
        "pricing.html",
        {"stripe_configured": settings.stripe_configured, "user": user},
    )
