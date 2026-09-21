from datetime import UTC, date, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlmodel import func, select

from ..config import settings
from ..db import SessionDep
from ..flash import flash
from ..models import Client, Invoice, InvoiceItem, User, compute_totals
from ..security import CurrentUser, RequiredUser
from ..services.pdf import render_invoice_pdf
from ..templating import render

router = APIRouter(tags=["invoices"])

VALID_STATUSES = {"draft", "sent", "paid"}


def _get_invoice(session: SessionDep, user: User, invoice_id: int) -> Invoice:
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.user_id != user.id:
        raise HTTPException(status_code=404)
    return invoice


def _get_items(session: SessionDep, invoice_id: int) -> list[InvoiceItem]:
    return list(
        session.exec(
            select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id)
        ).all()
    )


def _get_clients(session: SessionDep, user: User) -> list[Client]:
    return list(
        session.exec(
            select(Client).where(Client.user_id == user.id).order_by(Client.name)
        ).all()
    )


def _invoice_count(session: SessionDep, user: User) -> int:
    return session.exec(
        select(func.count()).select_from(Invoice).where(Invoice.user_id == user.id)
    ).one()


def _parse_items(form) -> list[tuple[str, float, float]]:
    descriptions = form.getlist("description")
    quantities = form.getlist("quantity")
    unit_prices = form.getlist("unit_price")
    items = []
    for i, description in enumerate(descriptions):
        description = description.strip()
        if not description:
            continue
        try:
            quantity = float(quantities[i])
        except (IndexError, ValueError, TypeError):
            quantity = 1.0
        try:
            unit_price = float(unit_prices[i])
        except (IndexError, ValueError, TypeError):
            unit_price = 0.0
        items.append((description, quantity, unit_price))
    return items


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@router.get("/dashboard")
def dashboard(request: Request, session: SessionDep, user: RequiredUser):
    invoices = list(
        session.exec(
            select(Invoice)
            .where(Invoice.user_id == user.id)
            .order_by(Invoice.id.desc())
        ).all()
    )
    rows = []
    outstanding = 0.0
    paid_total = 0.0
    draft_count = 0
    for invoice in invoices:
        totals = compute_totals(_get_items(session, invoice.id), invoice.tax_rate)
        if invoice.status == "sent":
            outstanding += totals["total"]
        elif invoice.status == "paid":
            paid_total += totals["total"]
        else:
            draft_count += 1
        rows.append({"invoice": invoice, "totals": totals})
    clients = {c.id: c for c in _get_clients(session, user)}
    return render(
        request,
        "dashboard.html",
        {
            "user": user,
            "invoice_count": len(invoices),
            "outstanding": outstanding,
            "paid_total": paid_total,
            "draft_count": draft_count,
            "recent": rows[:5],
            "clients": clients,
            "free_limit": settings.free_invoice_limit,
        },
    )


@router.get("/invoices")
def invoice_list(
    request: Request, session: SessionDep, user: RequiredUser, status: str | None = None
):
    invoices = list(
        session.exec(
            select(Invoice)
            .where(Invoice.user_id == user.id)
            .order_by(Invoice.id.desc())
        ).all()
    )
    counts = {"all": len(invoices)}
    for s in VALID_STATUSES:
        counts[s] = sum(1 for i in invoices if i.status == s)
    active_status = status if status in VALID_STATUSES else "all"
    if active_status != "all":
        invoices = [i for i in invoices if i.status == active_status]
    clients = {c.id: c for c in _get_clients(session, user)}
    rows = [
        {
            "invoice": invoice,
            "totals": compute_totals(_get_items(session, invoice.id), invoice.tax_rate),
        }
        for invoice in invoices
    ]
    return render(
        request,
        "invoices/list.html",
        {
            "user": user,
            "rows": rows,
            "clients": clients,
            "counts": counts,
            "active_status": active_status,
        },
    )


@router.get("/invoices/new")
def invoice_new(request: Request, session: SessionDep, user: RequiredUser):
    return render(
        request,
        "invoices/new.html",
        {
            "user": user,
            "clients": _get_clients(session, user),
            "today": datetime.now(UTC).date().isoformat(),
            "error": None,
        },
    )


@router.post("/invoices")
async def invoice_create(request: Request, session: SessionDep, user: RequiredUser):
    form = await request.form()
    count = _invoice_count(session, user)
    if not user.is_pro and count >= settings.free_invoice_limit:
        return RedirectResponse("/pricing?limit=1", 303)

    items = _parse_items(form)
    if not items:
        return render(
            request,
            "invoices/new.html",
            {
                "user": user,
                "clients": _get_clients(session, user),
                "today": datetime.now(UTC).date().isoformat(),
                "error": "Add at least one line item with a description.",
            },
            status_code=400,
        )

    client_id_raw = form.get("client_id", "")
    client_id = int(client_id_raw) if str(client_id_raw).isdigit() else None
    if client_id is not None:
        client = session.get(Client, client_id)
        if not client or client.user_id != user.id:
            client_id = None

    invoice = Invoice(
        user_id=user.id,
        client_id=client_id,
        number=f"INV-{count + 1:04d}",
        status="draft",
        currency=form.get("currency", "USD") or "USD",
        tax_rate=_float_or(form.get("tax_rate"), 0.0),
        issue_date=_parse_date(form.get("issue_date")) or datetime.now(UTC).date(),
        due_date=_parse_date(form.get("due_date")),
        notes=str(form.get("notes", "")).strip(),
    )
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    for description, quantity, unit_price in items:
        session.add(
            InvoiceItem(
                invoice_id=invoice.id,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
            )
        )
    session.commit()
    flash(request, f"Invoice {invoice.number} created.")
    return RedirectResponse(f"/invoices/{invoice.id}", 303)


def _float_or(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@router.get("/invoices/{invoice_id}")
def invoice_detail(
    request: Request, session: SessionDep, user: RequiredUser, invoice_id: int
):
    invoice = _get_invoice(session, user, invoice_id)
    items = _get_items(session, invoice.id)
    client = session.get(Client, invoice.client_id) if invoice.client_id else None
    return render(
        request,
        "invoices/detail.html",
        {
            "user": user,
            "invoice": invoice,
            "items": items,
            "client": client,
            "totals": compute_totals(items, invoice.tax_rate),
            "base_url": settings.base_url,
        },
    )


@router.get("/invoices/{invoice_id}/edit")
def invoice_edit_form(
    request: Request, session: SessionDep, user: RequiredUser, invoice_id: int
):
    invoice = _get_invoice(session, user, invoice_id)
    return render(
        request,
        "invoices/edit.html",
        {
            "user": user,
            "invoice": invoice,
            "items": _get_items(session, invoice.id),
            "clients": _get_clients(session, user),
            "error": None,
        },
    )


@router.post("/invoices/{invoice_id}/edit")
async def invoice_edit(
    request: Request, session: SessionDep, user: RequiredUser, invoice_id: int
):
    invoice = _get_invoice(session, user, invoice_id)
    form = await request.form()
    items = _parse_items(form)
    if not items:
        return render(
            request,
            "invoices/edit.html",
            {
                "user": user,
                "invoice": invoice,
                "items": _get_items(session, invoice.id),
                "clients": _get_clients(session, user),
                "error": "Add at least one line item with a description.",
            },
            status_code=400,
        )

    client_id_raw = form.get("client_id", "")
    client_id = int(client_id_raw) if str(client_id_raw).isdigit() else None
    if client_id is not None:
        client = session.get(Client, client_id)
        if not client or client.user_id != user.id:
            client_id = None

    invoice.client_id = client_id
    invoice.currency = form.get("currency", invoice.currency) or invoice.currency
    invoice.tax_rate = _float_or(form.get("tax_rate"), invoice.tax_rate)
    invoice.issue_date = _parse_date(form.get("issue_date")) or invoice.issue_date
    invoice.due_date = _parse_date(form.get("due_date"))
    invoice.notes = str(form.get("notes", "")).strip()
    session.add(invoice)

    for old_item in _get_items(session, invoice.id):
        session.delete(old_item)
    for description, quantity, unit_price in items:
        session.add(
            InvoiceItem(
                invoice_id=invoice.id,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
            )
        )
    session.commit()
    flash(request, f"Invoice {invoice.number} updated.")
    return RedirectResponse(f"/invoices/{invoice.id}", 303)


@router.post("/invoices/{invoice_id}/status")
async def invoice_status(
    request: Request, session: SessionDep, user: RequiredUser, invoice_id: int
):
    invoice = _get_invoice(session, user, invoice_id)
    form = await request.form()
    status = str(form.get("status", ""))
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    invoice.status = status
    session.add(invoice)
    session.commit()
    flash(request, f"Invoice marked as {status}.")
    return RedirectResponse(f"/invoices/{invoice.id}", 303)


@router.post("/invoices/{invoice_id}/delete")
def invoice_delete(
    request: Request, session: SessionDep, user: RequiredUser, invoice_id: int
):
    invoice = _get_invoice(session, user, invoice_id)
    for item in _get_items(session, invoice.id):
        session.delete(item)
    session.delete(invoice)
    session.commit()
    flash(request, "Invoice deleted.", "info")
    return RedirectResponse("/invoices", 303)


@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(request: Request, session: SessionDep, user: RequiredUser, invoice_id: int):
    invoice = _get_invoice(session, user, invoice_id)
    items = _get_items(session, invoice.id)
    client = session.get(Client, invoice.client_id) if invoice.client_id else None
    pdf_bytes = render_invoice_pdf(
        invoice, items, user, client, compute_totals(items, invoice.tax_rate)
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.number}.pdf"'},
    )


@router.get("/i/{share_token}")
def invoice_public(request: Request, session: SessionDep, user: CurrentUser, share_token: str):
    invoice = session.exec(
        select(Invoice).where(Invoice.share_token == share_token)
    ).first()
    if not invoice:
        raise HTTPException(status_code=404)
    items = _get_items(session, invoice.id)
    client = session.get(Client, invoice.client_id) if invoice.client_id else None
    owner = session.get(User, invoice.user_id)
    return render(
        request,
        "public_invoice.html",
        {
            "user": user,
            "invoice": invoice,
            "items": items,
            "client": client,
            "owner": owner,
            "totals": compute_totals(items, invoice.tax_rate),
        },
    )
