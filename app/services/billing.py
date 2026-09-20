import stripe
from sqlmodel import Session, select

from ..config import settings
from ..models import User


def _set_api_key() -> None:
    stripe.api_key = settings.stripe_secret_key


def is_configured() -> bool:
    return settings.stripe_configured


def create_checkout_session(session: Session, user: User) -> str:
    _set_api_key()
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.name,
            metadata={"user_id": str(user.id)},
        )
        user.stripe_customer_id = customer.id
        session.add(user)
        session.commit()
    checkout_session = stripe.checkout.Session.create(
        mode="subscription",
        customer=user.stripe_customer_id,
        line_items=[{"price": settings.pro_price_monthly_id, "quantity": 1}],
        success_url=f"{settings.base_url}/billing/success",
        cancel_url=f"{settings.base_url}/pricing",
        metadata={"user_id": str(user.id)},
    )
    return checkout_session.url


def create_portal_session(user: User) -> str:
    _set_api_key()
    portal_session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.base_url}/pricing",
    )
    return portal_session.url


def handle_webhook(session: Session, payload: bytes, sig_header: str) -> None:
    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret
    )
    data = event.data.object

    if event.type == "checkout.session.completed":
        user = None
        metadata = data.metadata or {}
        user_id = metadata.get("user_id")
        if user_id:
            user = session.get(User, int(user_id))
        if user is None and data.customer:
            user = session.exec(
                select(User).where(User.stripe_customer_id == data.customer)
            ).first()
        if user:
            if not user.stripe_customer_id:
                user.stripe_customer_id = data.customer
            user.is_pro = True
            session.add(user)
            session.commit()
    elif event.type in {"customer.subscription.updated", "customer.subscription.deleted"}:
        user = session.exec(
            select(User).where(User.stripe_customer_id == data.customer)
        ).first()
        if user:
            user.is_pro = data.status in {"active", "trialing"}
            session.add(user)
            session.commit()
