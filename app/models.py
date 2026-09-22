import secrets
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str = ""
    hashed_password: str
    is_pro: bool = False
    language: str = "zh-CN"
    document_language: str = "zh-CN"
    issuer_name: str = ""
    issuer_email: str = ""
    issuer_address: str = ""
    payment_instructions: str = ""
    default_currency: str = "USD"
    default_tax_rate: str = "0"
    invoice_sequence: int = 0
    stripe_customer_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Client(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str
    email: str = ""
    company: str = ""
    address: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Invoice(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    client_id: int | None = Field(default=None, foreign_key="client.id")
    number: str = Field(index=True)
    status: str = Field(default="draft")  # draft | sent | paid
    currency: str = Field(default="USD")
    tax_rate: float = 0.0
    tax_rate_decimal: str | None = None
    document_language: str = "en"
    issuer_snapshot: str | None = None
    client_snapshot: str | None = None
    payment_instructions: str = ""
    issue_date: date = Field(default_factory=date.today)
    due_date: date | None = None
    notes: str = ""
    share_token: str = Field(
        default_factory=lambda: secrets.token_urlsafe(16), index=True
    )
    created_at: datetime = Field(default_factory=utcnow)


class InvoiceItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id", index=True)
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    quantity_decimal: str | None = None
    unit_price_decimal: str | None = None


def decimal_value(value) -> Decimal:
    return Decimal(str(value))


def precision(currency: str) -> Decimal:
    return Decimal(1) if currency == "JPY" else Decimal("0.01")


def item_values(item) -> tuple[Decimal, Decimal]:
    if isinstance(item, dict):
        return decimal_value(item["quantity"]), decimal_value(item["unit_price"])
    return (
        decimal_value(item.quantity_decimal or item.quantity),
        decimal_value(item.unit_price_decimal or item.unit_price),
    )


def compute_totals(items: list, tax_rate, currency: str = "USD") -> dict:
    unit = precision(currency)
    subtotal = sum(
        (q * p).quantize(unit, rounding=ROUND_HALF_UP)
        for q, p in (item_values(i) for i in items)
    )
    subtotal = Decimal(subtotal).quantize(unit)
    tax = (subtotal * decimal_value(tax_rate) / 100).quantize(
        unit, rounding=ROUND_HALF_UP
    )
    return {"subtotal": subtotal, "tax": tax, "total": subtotal + tax}
