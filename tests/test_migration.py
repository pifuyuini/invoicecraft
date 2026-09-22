"""Upgrade a real legacy database without changing invoice identity or totals."""

import os
import sqlite3
import subprocess
import sys


def test_legacy_database_upgrade_preserves_records_and_makes_backup(tmp_path):
    database = tmp_path / "legacy.db"
    backup_dir = tmp_path / "backups"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
        CREATE TABLE user (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL, name VARCHAR NOT NULL, hashed_password VARCHAR NOT NULL, is_pro BOOLEAN NOT NULL, stripe_customer_id VARCHAR, created_at DATETIME NOT NULL);
        CREATE TABLE client (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name VARCHAR NOT NULL, email VARCHAR NOT NULL, company VARCHAR NOT NULL, address VARCHAR NOT NULL, notes VARCHAR NOT NULL, created_at DATETIME NOT NULL);
        CREATE TABLE invoice (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, client_id INTEGER, number VARCHAR NOT NULL, status VARCHAR NOT NULL, currency VARCHAR NOT NULL, tax_rate FLOAT NOT NULL, issue_date DATE NOT NULL, due_date DATE, notes VARCHAR NOT NULL, share_token VARCHAR NOT NULL, created_at DATETIME NOT NULL);
        CREATE TABLE invoiceitem (id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL, description VARCHAR NOT NULL, quantity FLOAT NOT NULL, unit_price FLOAT NOT NULL);
        INSERT INTO user VALUES (1, 'legacy@example.com', 'Legacy Studio', 'unused-test-value', 1, 'cus_test_legacy', '2026-09-01 00:00:00');
        INSERT INTO client VALUES (1, 1, '旧客户', 'old@example.com', '旧公司', '上海', '', '2026-09-01 00:00:00');
        INSERT INTO invoice VALUES (1, 1, 1, 'INV-0042', 'sent', 'USD', 10.0, '2026-09-01', '2026-10-01', 'Keep this note', 'keep-this-public-token', '2026-09-01 00:00:00');
        INSERT INTO invoiceitem VALUES (1, 1, '原始项目', 2.5, 120.25);
        """)
    env = os.environ.copy()
    env.update(
        DATABASE_URL=f"sqlite:///{database}",
        DATABASE_BACKUP_DIR=str(backup_dir),
        PYTHONDONTWRITEBYTECODE="1",
    )
    command = [
        sys.executable,
        "-B",
        "-c",
        "import app.models; from app.db import init_db; init_db()",
    ]
    result = subprocess.run(
        command, env=env, capture_output=True, text=True, timeout=30, check=False
    )
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT number, status, share_token, notes, document_language FROM invoice"
        ).fetchone() == (
            "INV-0042",
            "sent",
            "keep-this-public-token",
            "Keep this note",
            "en",
        )
        assert connection.execute(
            "SELECT quantity, unit_price FROM invoiceitem"
        ).fetchone() == (2.5, 120.25)
        assert connection.execute(
            "SELECT is_pro, stripe_customer_id FROM user"
        ).fetchone() == (1, "cus_test_legacy")
    backups = list(backup_dir.glob("*"))
    assert backups, "An existing database must be backed up before migration."
    second = subprocess.run(
        command, env=env, capture_output=True, text=True, timeout=30, check=False
    )
    assert second.returncode == 0, second.stderr
    assert list(backup_dir.glob("*")) == backups, (
        "A completed migration should not run again."
    )
