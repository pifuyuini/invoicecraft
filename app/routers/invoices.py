from datetime import UTC, date, datetime
from math import ceil
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlmodel import select

from ..config import settings
from ..db import SessionDep
from ..flash import flash
from ..models import Client, Invoice, User
from ..security import CurrentUser, RequiredUser
from ..services.invoicing import (
    add_items,
    apply_form,
    client_data,
    default_form,
    freeze_parties,
    invoice_document,
    invoice_items,
    invoice_rows,
    is_overdue,
    issuer_data,
    make_document,
    next_number,
    read_invoice_form,
    safe_return,
    summarize,
    validate_form,
)
from ..services.pdf import render_invoice_pdf
from ..templating import render, template_context, templates

router = APIRouter(tags=["invoices"])
VALID_STATUSES = {"draft", "sent", "paid"}


def _get_invoice(session, user, invoice_id):
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.user_id != user.id:
        raise HTTPException(status_code=404)
    return invoice


def _get_clients(session, user):
    return list(
        session.exec(
            select(Client).where(Client.user_id == user.id).order_by(Client.name)
        ).all()
    )


def _all_invoices(session, user):
    return list(
        session.exec(
            select(Invoice)
            .where(Invoice.user_id == user.id)
            .order_by(Invoice.id.desc())
        ).all()
    )


def _form_context(request, session, user, invoice=None, form=None, errors=None):
    items = invoice_items(session, invoice.id) if invoice else []
    return {
        "user": user,
        "invoice": invoice,
        "items": items,
        "clients": _get_clients(session, user),
        "form": form
        if form is not None
        else default_form(
            user, invoice, items, request.query_params.get("client_id", "")
        ),
        "errors": errors or {},
        "error": next(iter((errors or {}).values()), None),
        "today": datetime.now(UTC).date().isoformat(),
        "return_to": safe_return(request.query_params.get("return_to")),
    }


def _with_defaults(raw, user):
    form = read_invoice_form(raw)
    for key, value in default_form(user).items():
        if key != "items" and key not in raw:
            form[key] = value
    return form


def _detail_redirect(invoice, return_to=None):
    query = "?" + urlencode({"return_to": safe_return(return_to)}) if return_to else ""
    return RedirectResponse(f"/invoices/{invoice.id}{query}", 303)


@router.get("/dashboard")
def dashboard(request: Request, session: SessionDep, user: RequiredUser):
    invoices = _all_invoices(session, user)
    rows = invoice_rows(session, invoices)
    attention = sorted(
        (row for row in rows if row["invoice"].status in {"draft", "sent"}),
        key=lambda row: (
            not is_overdue(row["invoice"]),
            row["invoice"].due_date or date.max,
        ),
    )
    stats = {
        "invoice_count": len(invoices),
        "draft_count": sum(i.status == "draft" for i in invoices),
        "overdue_count": sum(is_overdue(i) for i in invoices),
    }
    return render(
        request,
        "dashboard.html",
        {
            "user": user,
            "summaries": summarize(rows),
            "stats": stats,
            "recent": rows[:6],
            "attention": attention[:6],
            "clients": {c.id: c for c in _get_clients(session, user)},
            **stats,
            "free_limit": settings.free_invoice_limit,
        },
    )


@router.get("/invoices")
def invoice_list(
    request: Request,
    session: SessionDep,
    user: RequiredUser,
    q: str = "",
    status: str = "all",
    currency: str = "",
    client_id: str = "",
    sort: str = "newest",
    page: int = 1,
):
    rows = invoice_rows(session, _all_invoices(session, user))
    counts = {
        "all": len(rows),
        **{
            key: sum(row["invoice"].status == key for row in rows)
            for key in VALID_STATUSES
        },
        "overdue": sum(is_overdue(row["invoice"]) for row in rows),
    }
    active_status = status if status in VALID_STATUSES | {"overdue"} else "all"
    if active_status != "all":
        rows = [
            row
            for row in rows
            if (
                is_overdue(row["invoice"])
                if active_status == "overdue"
                else row["invoice"].status == active_status
            )
        ]
    if currency:
        rows = [row for row in rows if row["invoice"].currency == currency]
    if client_id:
        rows = [row for row in rows if str(row["invoice"].client_id) == client_id]
    if q.strip():
        needle = q.strip().casefold()
        rows = [
            row
            for row in rows
            if needle in row["invoice"].number.casefold()
            or any(
                needle in str((row["client"] or {}).get(key, "")).casefold()
                for key in ("name", "company", "email")
            )
        ]
    valid_sorts = {"newest", "oldest", "due", "issue_desc", "issue_asc", "due_asc"}
    sort = sort if sort in valid_sorts else "newest"
    if sort in {"due", "due_asc"}:
        rows.sort(
            key=lambda row: (row["invoice"].due_date or date.max, row["invoice"].id)
        )
    else:
        rows.sort(
            key=lambda row: (row["invoice"].issue_date, row["invoice"].id),
            reverse=sort not in {"oldest", "issue_asc"},
        )
    total = len(rows)
    pages = max(1, ceil(total / 25))
    page = max(1, min(page, pages))
    return render(
        request,
        "invoices/list.html",
        {
            "user": user,
            "rows": rows[(page - 1) * 25 : page * 25],
            "clients": {c.id: c for c in _get_clients(session, user)},
            "counts": counts,
            "active_status": active_status,
            "filters": {
                "q": q,
                "status": active_status,
                "currency": currency,
                "client_id": client_id,
                "sort": sort,
            },
            "page": page,
            "pages": pages,
            "total": total,
            "count": total,
            "return_to": safe_return(
                str(request.url.path)
                + ("?" + request.url.query if request.url.query else "")
            ),
        },
    )


@router.get("/invoices/new")
def invoice_new(request: Request, session: SessionDep, user: RequiredUser):
    return render(request, "invoices/new.html", _form_context(request, session, user))


@router.post("/invoices/preview")
async def invoice_preview(request: Request, session: SessionDep, user: RequiredUser):
    raw = await request.form()
    form = _with_defaults(raw, user)
    errors, parsed = validate_form(form, session, user)
    if errors:
        return JSONResponse(
            {"html": "", "totals": {}, "errors": errors}, status_code=400
        )
    existing = None
    if str(raw.get("invoice_id", "")).isdigit():
        existing = _get_invoice(session, user, int(raw["invoice_id"]))
    invoice = Invoice(
        user_id=user.id,
        number=existing.number if existing else "DRAFT",
        status=existing.status if existing else "draft",
    )
    apply_form(invoice, form, parsed)
    freeze_parties(invoice, user, parsed["client"])
    issuer, recipient = issuer_data(user), client_data(parsed["client"])
    if existing and existing.status != "draft":
        old_doc = invoice_document(session, existing)
        issuer, recipient = old_doc["issuer"], old_doc["client"]
        invoice.payment_instructions = existing.payment_instructions
    doc = make_document(invoice, parsed["items"], issuer, recipient)
    context = template_context(
        request, {"user": user, "doc": doc, "invoice": invoice}, consume_flashes=False
    )
    html = templates.get_template("invoices/_document.html").render(context)
    return {
        "html": html,
        "totals": {key: str(value) for key, value in doc["totals"].items()},
        "errors": {},
    }


@router.post("/invoices")
async def invoice_create(request: Request, session: SessionDep, user: RequiredUser):
    raw = await request.form()
    if (
        settings.billing_enabled
        and not user.is_pro
        and len(_all_invoices(session, user)) >= settings.free_invoice_limit
    ):
        return RedirectResponse("/pricing?limit=1", 303)
    form = _with_defaults(raw, user)
    errors, parsed = validate_form(form, session, user)
    if errors:
        context = _form_context(request, session, user, form=form, errors=errors)
        context["return_to"] = safe_return(raw.get("return_to"))
        return render(request, "invoices/new.html", context, status_code=400)
    invoice = Invoice(user_id=user.id, number=next_number(session, user))
    apply_form(invoice, form, parsed)
    freeze_parties(invoice, user, parsed["client"])
    session.add(invoice)
    session.flush()
    add_items(session, invoice, parsed["items"])
    session.commit()
    flash(request, "Invoice created.")
    return _detail_redirect(invoice, raw.get("return_to"))


@router.get("/invoices/{invoice_id}")
def invoice_detail(
    request: Request, session: SessionDep, user: RequiredUser, invoice_id: int
):
    invoice = _get_invoice(session, user, invoice_id)
    doc = invoice_document(session, invoice)
    return render(
        request,
        "invoices/detail.html",
        {
            "user": user,
            "invoice": invoice,
            "items": invoice_items(session, invoice.id),
            "client": doc["client"],
            "totals": doc["totals"],
            "doc": doc,
            "base_url": settings.base_url,
            "return_to": safe_return(request.query_params.get("return_to")),
        },
    )


@router.get("/invoices/{invoice_id}/edit")
def invoice_edit_form(
    request: Request, session: SessionDep, user: RequiredUser, invoice_id: int
):
    invoice = _get_invoice(session, user, invoice_id)
    return render(
        request, "invoices/edit.html", _form_context(request, session, user, invoice)
    )


@router.post("/invoices/{invoice_id}/edit")
async def invoice_edit(
    request: Request, session: SessionDep, user: RequiredUser, invoice_id: int
):
    invoice = _get_invoice(session, user, invoice_id)
    raw = await request.form()
    form = _with_defaults(raw, user)
    errors, parsed = validate_form(form, session, user)
    if invoice.status != "draft" and str(invoice.client_id or "") != form["client_id"]:
        errors["client_id"] = "Duplicate this invoice to change the recipient."
    if errors:
        context = _form_context(request, session, user, invoice, form, errors)
        context["return_to"] = safe_return(raw.get("return_to"))
        return render(request, "invoices/edit.html", context, status_code=400)
    apply_form(invoice, form, parsed)
    if invoice.status == "draft":
        freeze_parties(invoice, user, parsed["client"])
    for old_item in invoice_items(session, invoice.id):
        session.delete(old_item)
    add_items(session, invoice, parsed["items"])
    session.add(invoice)
    session.commit()
    flash(request, "Invoice updated.")
    return _detail_redirect(invoice, raw.get("return_to"))


@router.post("/invoices/{invoice_id}/duplicate")
async def invoice_duplicate(
    request: Request, session: SessionDep, user: RequiredUser, invoice_id: int
):
    original = _get_invoice(session, user, invoice_id)
    raw = await request.form()
    form = default_form(user, original, invoice_items(session, original.id))
    form["issue_date"] = datetime.now(UTC).date().isoformat()
    if original.due_date and original.due_date < datetime.now(UTC).date():
        form["due_date"] = ""
    errors, parsed = validate_form(form, session, user)
    if errors:
        raise HTTPException(
            status_code=400,
            detail="This invoice cannot be copied until its values are corrected.",
        )
    invoice = Invoice(user_id=user.id, number=next_number(session, user))
    apply_form(invoice, form, parsed)
    freeze_parties(invoice, user, parsed["client"])
    session.add(invoice)
    session.flush()
    add_items(session, invoice, parsed["items"])
    session.commit()
    flash(request, "Invoice copied as a new draft.")
    return RedirectResponse(
        f"/invoices/{invoice.id}/edit?"
        + urlencode({"return_to": safe_return(raw.get("return_to"))}),
        303,
    )


@router.post("/invoices/{invoice_id}/status")
async def invoice_status(
    request: Request, session: SessionDep, user: RequiredUser, invoice_id: int
):
    invoice = _get_invoice(session, user, invoice_id)
    raw = await request.form()
    status = str(raw.get("status", ""))
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    invoice.status = status
    session.add(invoice)
    session.commit()
    flash(
        request,
        {
            "draft": "Invoice marked as draft.",
            "sent": "Invoice marked as sent. No email was sent.",
            "paid": "Invoice marked as paid.",
        }[status],
    )
    return _detail_redirect(invoice, raw.get("return_to"))


@router.post("/invoices/{invoice_id}/delete")
async def invoice_delete(
    request: Request, session: SessionDep, user: RequiredUser, invoice_id: int
):
    invoice = _get_invoice(session, user, invoice_id)
    raw = await request.form()
    for item in invoice_items(session, invoice.id):
        session.delete(item)
    session.delete(invoice)
    session.commit()
    flash(request, "Invoice deleted.", "info")
    return RedirectResponse(safe_return(raw.get("return_to")), 303)


@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(
    request: Request, session: SessionDep, user: RequiredUser, invoice_id: int
):
    invoice = _get_invoice(session, user, invoice_id)
    doc = invoice_document(session, invoice)
    client = session.get(Client, invoice.client_id) if invoice.client_id else None
    pdf_bytes = render_invoice_pdf(
        invoice,
        invoice_items(session, invoice.id),
        user,
        client,
        doc["totals"],
        doc=doc,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.number}.pdf"'},
    )


@router.get("/i/{share_token}")
def invoice_public(
    request: Request, session: SessionDep, user: CurrentUser, share_token: str
):
    invoice = session.exec(
        select(Invoice).where(Invoice.share_token == share_token)
    ).first()
    if not invoice:
        raise HTTPException(status_code=404)
    doc = invoice_document(session, invoice)
    return render(
        request,
        "public_invoice.html",
        {
            "user": user,
            "invoice": invoice,
            "items": invoice_items(session, invoice.id),
            "client": doc["client"],
            "owner": session.get(User, invoice.user_id),
            "totals": doc["totals"],
            "doc": doc,
            "lang": invoice.document_language,
        },
    )
