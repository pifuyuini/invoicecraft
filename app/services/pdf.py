from fpdf import FPDF

from ..models import Client, Invoice, InvoiceItem, User

_SYMBOLS = {"USD": "$", "EUR": "EUR ", "GBP": "£", "CNY": "¥", "JPY": "¥"}


def _safe(text: object) -> str:
    return str(text).encode("latin-1", "replace").decode("latin-1")


def _money(value: float, currency: str) -> str:
    symbol = _SYMBOLS.get(currency, f"{currency} ")
    return f"{symbol}{value:,.2f}"


def render_invoice_pdf(
    invoice: Invoice,
    items: list[InvoiceItem],
    user: User,
    client: Client | None,
    totals: dict,
) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Header: seller on the left, INVOICE + number on the right
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(100, 10, _safe(user.name or user.email))
    pdf.set_font("helvetica", "B", 24)
    pdf.cell(0, 10, "INVOICE", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(100, 6, _safe(user.email))
    pdf.cell(0, 6, _safe(invoice.number), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Bill-to block (left) and dates block (right), starting at the same Y
    top_y = pdf.get_y()
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(100, 6, "Bill to:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    bill_lines = []
    if client:
        bill_lines = [l for l in [client.name, client.company, client.email] if l]
        if client.address:
            bill_lines.append(client.address)
    if not bill_lines:
        bill_lines = ["-"]
    for line in bill_lines:
        pdf.multi_cell(90, 5, _safe(line))
    left_bottom = pdf.get_y()

    pdf.set_xy(120, top_y)
    for label, value in [
        ("Issue date:", invoice.issue_date.isoformat()),
        ("Due date:", invoice.due_date.isoformat() if invoice.due_date else "-"),
        ("Status:", invoice.status.upper()),
    ]:
        pdf.set_x(120)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(35, 6, label)
        pdf.set_font("helvetica", "", 10)
        pdf.cell(35, 6, _safe(value), new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(max(left_bottom, pdf.get_y()) + 8)

    # Items table
    col_w = [90, 25, 35, 40]
    headers = ["Description", "Qty", "Unit price", "Amount"]
    pdf.set_font("helvetica", "B", 10)
    for w, h in zip(col_w, headers):
        pdf.cell(w, 8, h, border=1, align="L" if h == "Description" else "R")
    pdf.ln()
    pdf.set_font("helvetica", "", 10)
    for item in items:
        pdf.cell(col_w[0], 7, _safe(item.description)[:60], border=1)
        pdf.cell(col_w[1], 7, f"{item.quantity:g}", border=1, align="R")
        pdf.cell(col_w[2], 7, _safe(_money(item.unit_price, invoice.currency)), border=1, align="R")
        pdf.cell(col_w[3], 7, _safe(_money(item.quantity * item.unit_price, invoice.currency)), border=1, align="R")
        pdf.ln()

    # Totals
    def total_row(label: str, value: str, bold: bool = False) -> None:
        pdf.set_font("helvetica", "B" if bold else "", 10)
        pdf.cell(sum(col_w[:3]), 7, label, align="R")
        pdf.cell(col_w[3], 7, _safe(value), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    total_row("Subtotal", _money(totals["subtotal"], invoice.currency))
    total_row(f"Tax ({invoice.tax_rate:g}%)", _money(totals["tax"], invoice.currency))
    total_row("Total", _money(totals["total"], invoice.currency), bold=True)

    # Notes
    if invoice.notes:
        pdf.ln(8)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, "Notes", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 5, _safe(invoice.notes))

    if not user.is_pro:
        pdf.set_y(-18)
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 6, "Created with InvoiceCraft", align="C")

    return bytes(pdf.output())
