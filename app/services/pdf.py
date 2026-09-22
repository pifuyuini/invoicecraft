"""Unicode invoices rendered from the same immutable document as the web view."""

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from fpdf import FPDF

from ..config import settings
from ..models import Client, Invoice, InvoiceItem, User

_FONT = Path(__file__).resolve().parents[1] / "static/fonts/NotoSansSC-Regular.ttf"
_INK = (43, 43, 39)
_MUTED = (119, 114, 105)
_ACCENT = (163, 85, 62)
_RULE = (224, 218, 207)
_PAPER = (247, 244, 239)
_LABELS = {
    "en": {
        "invoice": "INVOICE", "bill_to": "BILL TO", "issued": "Issued",
        "due": "Due", "description": "Description", "quantity": "Qty",
        "unit_price": "Unit price", "amount": "Amount", "subtotal": "Subtotal",
        "tax": "Tax", "total": "Total", "notes": "Notes",
        "payment": "Payment instructions", "page": "Page",
        "draft": "Draft", "sent": "Sent", "paid": "Paid", "overdue": "Overdue",
        "watermark": "Created with InvoiceCraft",
    },
    "zh-CN": {
        "invoice": "账单", "bill_to": "账单接收方", "issued": "开具日期",
        "due": "到期日期", "description": "项目描述", "quantity": "数量",
        "unit_price": "单价", "amount": "金额", "subtotal": "小计",
        "tax": "税额", "total": "合计", "notes": "备注",
        "payment": "付款说明", "page": "页",
        "draft": "草稿", "sent": "已发送", "paid": "已收款", "overdue": "已逾期",
        "watermark": "使用 InvoiceCraft 制作",
    },
}


def _decimal(value: object) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _money(value: object, currency: str) -> str:
    precision = 0 if currency == "JPY" else 2
    rounded = _decimal(value).quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP)
    return f"{rounded:,.{precision}f}"


def _plain_number(value: object) -> str:
    return format(_decimal(value).normalize(), "f")


def _date(value: object) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value or "-")


def _fallback_document(invoice, items, user, client, totals) -> dict:
    """Retain the original call contract for integrations without a document."""
    return {
        "number": invoice.number,
        "currency": invoice.currency,
        "language": getattr(invoice, "language", "en"),
        "status": invoice.status,
        "issue_date": invoice.issue_date,
        "due_date": invoice.due_date,
        "issuer": {
            "name": getattr(user, "issuer_name", None) or user.name or user.email,
            "email": getattr(user, "issuer_email", None) or user.email,
            "address": getattr(user, "issuer_address", ""),
        },
        "client": {
            key: getattr(client, key, "") for key in ("name", "company", "email", "address")
        } if client else None,
        "items": [{
            "description": item.description,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "amount": _decimal(item.quantity) * _decimal(item.unit_price),
        } for item in items],
        "totals": totals,
        "tax_rate": invoice.tax_rate,
        "notes": invoice.notes,
        "payment_instructions": getattr(user, "payment_instructions", ""),
    }


class _InvoicePDF(FPDF):
    def __init__(self, document: dict, watermark: bool):
        super().__init__(format="A4")
        self.document = document
        self.labels = _LABELS.get(document.get("language"), _LABELS["en"])
        self.watermark = watermark
        self.set_margins(18, 24, 18)
        self.set_auto_page_break(True, margin=21)
        self.add_font("Studio", fname=str(_FONT))
        self.set_title(f"{self.labels['invoice']} {document['number']}")
        self.set_author(document["issuer"].get("name") or "InvoiceCraft")
        self.set_creator("InvoiceCraft")

    def header(self):
        self.set_fill_color(255, 255, 255)
        self.rect(0, 0, self.w, self.h, style="F")
        self.set_xy(self.l_margin, 12)
        self.set_font("Studio", size=8)
        self.set_text_color(*_ACCENT)
        self.cell(90, 5, "INVOICECRAFT")
        self.set_text_color(*_MUTED)
        self.cell(0, 5, str(self.document["number"]), align="R")
        self.set_draw_color(*_RULE)
        self.line(self.l_margin, 20, self.w - self.r_margin, 20)
        self.set_y(26)

    def footer(self):
        self.set_y(-15)
        self.set_font("Studio", size=8)
        self.set_text_color(*_MUTED)
        self.cell(90, 5, self.labels["watermark"] if self.watermark else "")
        self.cell(0, 5, f"{self.labels['page']} {self.page_no()}", align="R")


def _text(pdf: FPDF, text: object, width: float = 0, *, size=10, color=_INK, height=5.8):
    pdf.set_font("Studio", size=size)
    pdf.set_text_color(*color)
    pdf.multi_cell(width, height, str(text or ""), align="L", new_x="LMARGIN", new_y="NEXT")


def _intro(pdf: _InvoicePDF, doc: dict):
    labels = pdf.labels
    issuer = doc["issuer"]
    top = pdf.get_y() + 3
    pdf.set_xy(126, top)
    _text(pdf, labels["invoice"], 66, size=27, color=_ACCENT, height=13)
    status = doc["status"]
    due = doc.get("due_date")
    if isinstance(due, str) and due:
        due = date.fromisoformat(due)
    if status == "sent" and due and due < datetime.now(UTC).date():
        status = "overdue"
    pdf.set_x(126)
    _text(pdf, labels.get(status, status), 66, size=10, color=_MUTED)
    right_bottom = pdf.get_y()
    pdf.set_xy(18, top + 1)
    _text(pdf, issuer.get("name") or "InvoiceCraft", 101, size=18, height=8)
    for key in ("email", "address"):
        if issuer.get(key):
            _text(pdf, issuer[key], 101, size=9, color=_MUTED, height=5)
    pdf.set_y(max(pdf.get_y(), right_bottom) + 13)

    # Keep dates in a separate, compact column beside the recipient details.
    top = pdf.get_y()
    pdf.set_xy(126, top)
    for key, value in (("issued", doc["issue_date"]), ("due", due)):
        pdf.set_x(126)
        pdf.set_font("Studio", size=8.5)
        pdf.set_text_color(*_MUTED)
        pdf.cell(25, 7, labels[key])
        pdf.set_text_color(*_INK)
        pdf.cell(41, 7, _date(value), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(126)
    _text(pdf, doc["currency"], 66, size=9, color=_MUTED)
    right_bottom = pdf.get_y()
    pdf.set_xy(18, top)
    _text(pdf, labels["bill_to"], 100, size=8, color=_ACCENT, height=6)
    recipient = doc.get("client") or {}
    for key in ("name", "company", "email", "address"):
        if recipient.get(key):
            _text(pdf, recipient[key], 100, size=10 if key == "name" else 9, height=5)
    if not any(recipient.values()):
        _text(pdf, "-", 100)
    pdf.set_y(max(pdf.get_y(), right_bottom) + 12)


def _items_table(pdf: _InvoicePDF, doc: dict):
    widths = (86, 16, 35, 37)
    line_height = 5.5

    def heading():
        pdf.set_fill_color(*_PAPER)
        pdf.set_text_color(*_MUTED)
        pdf.set_font("Studio", size=8)
        pdf.set_x(18)
        for width, key in zip(widths, ("description", "quantity", "unit_price", "amount")):
            pdf.cell(width, 10, pdf.labels[key], align="L" if key == "description" else "R", fill=True)
        pdf.ln(10)

    def next_page():
        pdf.add_page()
        heading()

    if pdf.get_y() + 25 > pdf.page_break_trigger:
        pdf.add_page()
    heading()
    for item in doc["items"]:
        pdf.set_font("Studio", size=9)
        lines = pdf.multi_cell(
            widths[0] - 6, line_height, str(item["description"]),
            dry_run=True, output="LINES", align="L", new_x="LMARGIN", new_y="NEXT",
        ) or [""]
        # Keep ordinary rows together. An unusually long description may span pages.
        row_height = len(lines) * line_height + 8
        if row_height <= 230 and pdf.get_y() + row_height > pdf.page_break_trigger:
            next_page()
        first_chunk = True
        while lines:
            available_lines = int((pdf.page_break_trigger - pdf.get_y() - 8) // line_height)
            if available_lines < 1:
                next_page()
                continue
            chunk, lines = lines[:available_lines], lines[available_lines:]
            top = pdf.get_y()
            pdf.set_xy(18, top + 4)
            _text(pdf, "\n".join(chunk), widths[0] - 6, size=9, height=line_height)
            if first_chunk:
                x = 18 + widths[0]
                for width, value in zip(widths[1:], (
                    _plain_number(item["quantity"]),
                    _money(item["unit_price"], doc["currency"]),
                    _money(item["amount"], doc["currency"]),
                )):
                    pdf.set_xy(x, top + 4)
                    pdf.set_font("Studio", size=9)
                    text_width = pdf.get_string_width(value)
                    if text_width > width - 3:
                        pdf.set_font("Studio", size=9 * (width - 3) / text_width)
                    pdf.cell(width, line_height, value, align="R")
                    x += width
                first_chunk = False
            bottom = top + len(chunk) * line_height + 8
            pdf.set_draw_color(*_RULE)
            pdf.line(18, bottom, 192, bottom)
            pdf.set_xy(18, bottom)
            if lines:
                next_page()


def _totals_and_notes(pdf: _InvoicePDF, doc: dict):
    if pdf.get_y() + 40 > pdf.page_break_trigger:
        pdf.add_page()
    pdf.ln(7)
    for key, label in (
        ("subtotal", pdf.labels["subtotal"]),
        ("tax", f"{pdf.labels['tax']} ({_plain_number(doc['tax_rate'])}%)"),
        ("total", pdf.labels["total"]),
    ):
        pdf.set_x(109)
        pdf.set_font("Studio", size=12 if key == "total" else 9)
        pdf.set_text_color(*(_ACCENT if key == "total" else _MUTED))
        pdf.cell(33, 10 if key == "total" else 7, label)
        value = _money(doc["totals"][key], doc["currency"])
        if key == "total":
            value = f"{doc['currency']} {value}"
        # Large legitimate totals fit without colliding with their label.
        if pdf.get_string_width(value) > 48:
            pdf.set_font("Studio", size=pdf.font_size_pt * 48 / pdf.get_string_width(value))
        pdf.cell(50, 10 if key == "total" else 7, value, align="R", new_x="LMARGIN", new_y="NEXT")
    for key, label in (("notes", "notes"), ("payment_instructions", "payment")):
        if not doc.get(key):
            continue
        if pdf.get_y() + 25 > pdf.page_break_trigger:
            pdf.add_page()
        pdf.ln(9)
        _text(pdf, pdf.labels[label], size=9, color=_ACCENT, height=7)
        _text(pdf, doc[key], size=9, color=_MUTED, height=5.8)


def render_invoice_pdf(
    invoice: Invoice,
    items: list[InvoiceItem],
    user: User,
    client: Client | None,
    totals: dict,
    *,
    doc: dict | None = None,
) -> bytes:
    document = doc if doc is not None else _fallback_document(invoice, items, user, client, totals)
    watermark = settings.billing_enabled and not user.is_pro
    pdf = _InvoicePDF(document, watermark=watermark)
    pdf.add_page()
    _intro(pdf, document)
    _items_table(pdf, document)
    _totals_and_notes(pdf, document)
    return bytes(pdf.output())
