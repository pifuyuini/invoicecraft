import stripe
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..config import settings
from ..db import SessionDep
from ..security import RequiredUser
from ..services import billing as billing_service
from ..templating import templates

router = APIRouter(tags=["billing"])


@router.post("/billing/checkout")
def checkout(session: SessionDep, user: RequiredUser):
    if not billing_service.is_configured():
        return RedirectResponse("/pricing?unavailable=1", 303)
    try:
        url = billing_service.create_checkout_session(session, user)
    except stripe.StripeError:
        return RedirectResponse("/pricing?unavailable=1", 303)
    return RedirectResponse(url, 303)


@router.post("/billing/portal")
def portal(user: RequiredUser):
    if not billing_service.is_configured() or not user.stripe_customer_id:
        return RedirectResponse("/pricing", 303)
    try:
        url = billing_service.create_portal_session(user)
    except stripe.StripeError:
        return RedirectResponse("/pricing", 303)
    return RedirectResponse(url, 303)


@router.get("/billing/success")
def success(request: Request, user: RequiredUser):
    return templates.TemplateResponse(request, "billing/success.html", {"user": user})


@router.post("/billing/webhook")
async def webhook(request: Request, session: SessionDep):
    if not settings.stripe_configured or not settings.stripe_webhook_secret:
        raise HTTPException(status_code=400)
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        billing_service.handle_webhook(session, payload, sig_header)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="invalid signature")
    return {"ok": True}
