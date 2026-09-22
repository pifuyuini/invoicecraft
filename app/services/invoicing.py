"""One amount/document pipeline shared by preview, stored invoices and PDF."""

import json
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from urllib.parse import urlsplit

from sqlalchemy import update
from sqlmodel import select

from ..models import (
    Client,
    InvoiceItem,
    User,
    compute_totals,
    item_values,
    precision,
)

CURRENCIES = ["USD", "EUR", "GBP", "CNY", "JPY"]
LANGUAGES = {"zh-CN", "en"}


def is_overdue(invoice) -> bool:
    return (
        invoice.status == "sent"
        and invoice.due_date is not None
        and invoice.due_date < datetime.now(UTC).date()
    )


def safe_return(value: str | None, default: str = "/invoices") -> str:
    value = str(value or "")
    parts = urlsplit(value)
    if (
        parts.scheme
        or parts.netloc
        or not parts.path.startswith("/")
        or value.startswith("//")
        or "\\" in value
    ):
        return default
    if not (
        parts.path == "/invoices"
        or parts.path == "/clients"
        or parts.path == "/dashboard"
        or parts.path.startswith("/clients/")
    ):
        return default
    return value


def invoice_items(session, invoice_id):
    return list(
        session.exec(
            select(InvoiceItem)
            .where(InvoiceItem.invoice_id == invoice_id)
            .order_by(InvoiceItem.id)
        ).all()
    )


def issuer_data(user):
    return {
        "name": user.issuer_name or user.name,
        "email": user.issuer_email or user.email,
        "address": user.issuer_address,
    }


def client_data(client):
    return (
        {key: getattr(client, key) for key in ("name", "company", "email", "address")}
        if client
        else None
    )


def freeze_parties(invoice, user, client):
    invoice.issuer_snapshot = json.dumps(issuer_data(user), ensure_ascii=False)
    invoice.client_snapshot = json.dumps(client_data(client), ensure_ascii=False)
    invoice.payment_instructions = user.payment_instructions


def invoice_document(session, invoice):
    user = session.get(User, invoice.user_id)
    client = session.get(Client, invoice.client_id) if invoice.client_id else None
    issuer = (
        json.loads(invoice.issuer_snapshot)
        if invoice.issuer_snapshot
        else issuer_data(user)
    )
    recipient = (
        json.loads(invoice.client_snapshot)
        if invoice.client_snapshot
        else client_data(client)
    )
    return make_document(invoice, invoice_items(session, invoice.id), issuer, recipient)


def make_document(invoice, items, issuer, client):
    tax_rate = Decimal(invoice.tax_rate_decimal or str(invoice.tax_rate))
    rows = []
    for item in items:
        quantity, unit_price = item_values(item)
        rows.append(
            {
                "description": item["description"]
                if isinstance(item, dict)
                else item.description,
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": (quantity * unit_price).quantize(
                    precision(invoice.currency), rounding=ROUND_HALF_UP
                ),
            }
        )
    return {
        "number": invoice.number,
        "currency": invoice.currency,
        "language": invoice.document_language,
        "status": invoice.status,
        "issue_date": invoice.issue_date,
        "due_date": invoice.due_date,
        "issuer": issuer,
        "client": client,
        "items": rows,
        "totals": compute_totals(items, tax_rate, invoice.currency),
        "tax_rate": tax_rate,
        "notes": invoice.notes,
        "payment_instructions": invoice.payment_instructions,
    }


def next_number(session, user):
    sequence = session.execute(
        update(User)
        .where(User.id == user.id)
        .values(invoice_sequence=User.invoice_sequence + 1)
        .returning(User.invoice_sequence)
    ).scalar_one()
    return f"INV-{sequence:04d}"


def numeric(value, key, errors, *, maximum=Decimal(1000000000000), places=6):
    try:
        parsed = Decimal(str(value))
        if not parsed.is_finite() or parsed < 0 or parsed > maximum:
            raise InvalidOperation
        if parsed.as_tuple().exponent < -places:
            errors[key] = (
                "Use at most six decimal places."
                if places == 6
                else "Use at most four decimal places."
            )
            return None
        return parsed
    except (InvalidOperation, ValueError, TypeError):
        errors[key] = "Enter a valid non-negative number."
        return None


def default_form(user, invoice=None, items=None, client_id=""):
    if invoice:
        return {
            "client_id": str(invoice.client_id or ""),
            "currency": invoice.currency,
            "tax_rate": invoice.tax_rate_decimal or str(invoice.tax_rate),
            "issue_date": invoice.issue_date.isoformat(),
            "due_date": invoice.due_date.isoformat() if invoice.due_date else "",
            "notes": invoice.notes,
            "document_language": invoice.document_language,
            "items": [
                {
                    "description": item.description,
                    "quantity": str(item_values(item)[0]),
                    "unit_price": str(item_values(item)[1]),
                }
                for item in items or []
            ],
        }
    return {
        "client_id": str(client_id or ""),
        "currency": user.default_currency,
        "tax_rate": user.default_tax_rate,
        "issue_date": datetime.now(UTC).date().isoformat(),
        "due_date": "",
        "notes": "",
        "document_language": user.document_language,
        "items": [{"description": "", "quantity": "1", "unit_price": "0"}],
    }


def read_invoice_form(raw):
    form = {
        key: str(raw.get(key, ""))
        for key in (
            "client_id",
            "currency",
            "tax_rate",
            "issue_date",
            "due_date",
            "notes",
            "document_language",
        )
    }
    descriptions, quantities, prices = (
        raw.getlist("description"),
        raw.getlist("quantity"),
        raw.getlist("unit_price"),
    )
    form["items"] = [
        {
            "description": str(descriptions[i]) if i < len(descriptions) else "",
            "quantity": str(quantities[i]) if i < len(quantities) else "",
            "unit_price": str(prices[i]) if i < len(prices) else "",
        }
        for i in range(max(len(descriptions), len(quantities), len(prices)))
    ]
    return form


def validate_form(form, session, user):
    errors = {}
    client = None
    if form["client_id"]:
        if form["client_id"].isdigit():
            client = session.get(Client, int(form["client_id"]))
        if not client or client.user_id != user.id:
            errors["client_id"] = "Select a valid client."
    if form["currency"] not in CURRENCIES:
        errors["currency"] = "Select a supported currency."
    if form["document_language"] not in LANGUAGES:
        errors["document_language"] = "Select a document language."
    tax_rate = numeric(
        form["tax_rate"], "tax_rate", errors, maximum=Decimal(100), places=4
    )
    dates = {}
    for key in ("issue_date", "due_date"):
        try:
            dates[key] = date.fromisoformat(form[key]) if form[key] else None
        except ValueError:
            dates[key] = None
            errors[key] = "Enter a valid date."
    if not dates["issue_date"]:
        errors["issue_date"] = "Issue date is required."
    if (
        dates["due_date"]
        and dates["issue_date"]
        and dates["due_date"] < dates["issue_date"]
    ):
        errors["due_date"] = "Due date cannot be before issue date."
    items = []
    if not form["items"]:
        errors["items"] = "Add at least one line item with a description."
    for index, row in enumerate(form["items"]):
        if not row["description"].strip():
            errors[f"description_{index}"] = "Description is required."
        quantity = numeric(row["quantity"], f"quantity_{index}", errors)
        unit_price = numeric(row["unit_price"], f"unit_price_{index}", errors)
        if quantity is not None and unit_price is not None:
            items.append(
                {
                    "description": row["description"].strip(),
                    "quantity": quantity,
                    "unit_price": unit_price,
                }
            )
    return errors, {"client": client, "tax_rate": tax_rate, **dates, "items": items}


def apply_form(invoice, form, parsed):
    invoice.client_id = parsed["client"].id if parsed["client"] else None
    invoice.currency = form["currency"]
    invoice.tax_rate = float(parsed["tax_rate"])
    invoice.tax_rate_decimal = str(parsed["tax_rate"])
    invoice.issue_date = parsed["issue_date"]
    invoice.due_date = parsed["due_date"]
    invoice.notes = form["notes"].strip()
    invoice.document_language = form["document_language"]


def add_items(session, invoice, rows):
    for row in rows:
        session.add(
            InvoiceItem(
                invoice_id=invoice.id,
                description=row["description"],
                quantity=float(row["quantity"]),
                unit_price=float(row["unit_price"]),
                quantity_decimal=str(row["quantity"]),
                unit_price_decimal=str(row["unit_price"]),
            )
        )


def invoice_rows(session, invoices):
    rows = []
    for invoice in invoices:
        doc = invoice_document(session, invoice)
        rows.append(
            {"invoice": invoice, "client": doc["client"], "totals": doc["totals"]}
        )
    return rows


def summarize(rows):
    grouped = {}
    for row in rows:
        invoice = row["invoice"]
        entry = grouped.setdefault(
            invoice.currency,
            {
                "currency": invoice.currency,
                "outstanding": Decimal(0),
                "overdue": Decimal(0),
                "paid": Decimal(0),
            },
        )
        if invoice.status == "sent":
            entry["outstanding"] += row["totals"]["total"]
            if is_overdue(invoice):
                entry["overdue"] += row["totals"]["total"]
        elif invoice.status == "paid":
            entry["paid"] += row["totals"]["total"]
    return [grouped[key] for key in sorted(grouped)]
