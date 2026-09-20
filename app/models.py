import secrets
from datetime import UTC, date, datetime

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str = ""
    hashed_password: str
    is_pro: bool = False
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
    issue_date: date = Field(default_factory=date.today)
    due_date: date | None = None
    notes: str = ""
    share_token: str = Field(default_factory=lambda: secrets.token_urlsafe(16), index=True)
    created_at: datetime = Field(default_factory=utcnow)


class InvoiceItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id", index=True)
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0


def compute_totals(items: list[InvoiceItem], tax_rate: float) -> dict:
    subtotal = sum(i.quantity * i.unit_price for i in items)
    tax = subtotal * tax_rate / 100
    return {"subtotal": subtotal, "tax": tax, "total": subtotal + tax}
