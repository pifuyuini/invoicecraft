import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from . import models  # noqa: F401 — register tables before schema inspection
from .config import settings

if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.removeprefix("sqlite:///")
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        settings.database_url, connect_args={"check_same_thread": False, "timeout": 30}
    )
else:
    engine = create_engine(settings.database_url)


MIGRATION_COLUMNS = {
    "user": {
        "language": "TEXT NOT NULL DEFAULT 'zh-CN'",
        "document_language": "TEXT NOT NULL DEFAULT 'zh-CN'",
        "issuer_name": "TEXT NOT NULL DEFAULT ''",
        "issuer_email": "TEXT NOT NULL DEFAULT ''",
        "issuer_address": "TEXT NOT NULL DEFAULT ''",
        "payment_instructions": "TEXT NOT NULL DEFAULT ''",
        "default_currency": "TEXT NOT NULL DEFAULT 'USD'",
        "default_tax_rate": "TEXT NOT NULL DEFAULT '0'",
        "invoice_sequence": "INTEGER NOT NULL DEFAULT 0",
    },
    "invoice": {
        "tax_rate_decimal": "TEXT",
        "document_language": "TEXT NOT NULL DEFAULT 'en'",
        "issuer_snapshot": "TEXT",
        "client_snapshot": "TEXT",
        "payment_instructions": "TEXT NOT NULL DEFAULT ''",
    },
    "invoiceitem": {"quantity_decimal": "TEXT", "unit_price_decimal": "TEXT"},
}


def init_db() -> None:
    inspector = inspect(engine)
    existing = inspector.get_table_names()
    if engine.dialect.name != "sqlite":
        SQLModel.metadata.create_all(engine)
        return
    version = 0
    if "schema_migrations" in existing:
        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
            ).scalar()
    if version >= 1:
        SQLModel.metadata.create_all(engine)
        return
    if "user" in existing and db_path != ":memory:":
        backup_dir = Path(settings.database_backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / (
            Path(db_path).stem
            + "-before-studio-"
            + datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
            + ".db"
        )
        with sqlite3.connect(db_path) as source, sqlite3.connect(backup) as destination:
            source.backup(destination)
    SQLModel.metadata.create_all(engine)
    with engine.begin() as connection:
        for table, additions in MIGRATION_COLUMNS.items():
            columns = {
                row[1]
                for row in connection.execute(text(f'PRAGMA table_info("{table}")'))
            }
            for column, definition in additions.items():
                if column not in columns:
                    connection.execute(
                        text(
                            f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}'
                        )
                    )
        connection.execute(
            text(
                "UPDATE invoice SET tax_rate_decimal = CAST(tax_rate AS TEXT) WHERE tax_rate_decimal IS NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE invoiceitem SET quantity_decimal = CAST(quantity AS TEXT), unit_price_decimal = CAST(unit_price AS TEXT) WHERE quantity_decimal IS NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE user SET issuer_name = name, issuer_email = email WHERE issuer_name = '' AND issuer_email = ''"
            )
        )
        for user_id, sequence in connection.execute(
            text("SELECT id, invoice_sequence FROM user")
        ).all():
            numbers = (
                connection.execute(
                    text("SELECT number FROM invoice WHERE user_id = :user_id"),
                    {"user_id": user_id},
                )
                .scalars()
                .all()
            )
            maximum = max(
                [sequence]
                + [
                    int(n[4:])
                    for n in numbers
                    if n.startswith("INV-") and n[4:].isdigit()
                ]
            )
            connection.execute(
                text(
                    "UPDATE user SET invoice_sequence = :sequence WHERE id = :user_id"
                ),
                {"sequence": maximum, "user_id": user_id},
            )
        # Freeze existing documents before later customer or issuer edits.
        invoices = connection.execute(
            text(
                "SELECT id, user_id, client_id FROM invoice WHERE issuer_snapshot IS NULL"
            )
        ).all()
        import json

        for invoice_id, user_id, client_id in invoices:
            user = connection.execute(
                text(
                    "SELECT issuer_name, issuer_email, issuer_address, payment_instructions FROM user WHERE id = :id"
                ),
                {"id": user_id},
            ).first()
            client = (
                connection.execute(
                    text(
                        "SELECT name, company, email, address FROM client WHERE id = :id"
                    ),
                    {"id": client_id},
                ).first()
                if client_id
                else None
            )
            issuer = (
                dict(zip(("name", "email", "address"), user[:3]))
                if user
                else {"name": "", "email": "", "address": ""}
            )
            recipient = (
                dict(zip(("name", "company", "email", "address"), client))
                if client
                else None
            )
            connection.execute(
                text(
                    "UPDATE invoice SET issuer_snapshot = :issuer, client_snapshot = :client, payment_instructions = :payment WHERE id = :id"
                ),
                {
                    "issuer": json.dumps(issuer, ensure_ascii=False),
                    "client": json.dumps(recipient, ensure_ascii=False),
                    "payment": user[3] if user else "",
                    "id": invoice_id,
                },
            )
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
        )
        connection.execute(
            text("INSERT INTO schema_migrations VALUES (1, :now)"),
            {"now": datetime.now(UTC).isoformat()},
        )


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
