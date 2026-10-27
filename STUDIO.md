# InvoiceCraft Studio

A bilingual invoicing workspace for independent studios, presented as an IC–80 Cassette Futurism console. This version remains a FastAPI/Jinja application; macOS packaging and offline operation are future work.

## Run with the existing environment

Run from the repository root using its existing `.venv`:

```sh
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The application supports the original environment variables plus:

- `BILLING_ENABLED=false`: the default. Removes invoice quotas and upgrade UI; PDF exports have no free-plan watermark. Existing subscription records and webhook processing are preserved.
- `SESSION_COOKIE=session`: change this when comparing two previews on the same hostname, because browser cookies do not distinguish ports.
- `DATABASE_BACKUP_DIR`: location for pre-migration SQLite backups. Set this explicitly for each deployment or isolated preview.

Use a separate `DATABASE_URL`, `SECRET_KEY`, `BASE_URL`, and `SESSION_COOKIE` for previews. Do not point a test or preview at the production database. Startup applies versioned SQLite migrations and backs up an existing database before schema changes. Keep the backup until the upgrade has been accepted.

## Working with invoices

1. Set the issuer, contact address, payment instructions, default currency/tax and document language in Settings.
2. Add a client or create one directly in the invoice editor.
3. Edit items and inspect the server-calculated document preview. Saving is explicit; previewing does not create an invoice.
4. Download the PDF or copy the public sharing link.
5. Mark sent or paid when the corresponding real-world action is complete. The application does not send email, collect payment or reconcile transactions.

Interface language and document language are independent. Existing invoices retain English as their document language. Saved issuer/client snapshots protect sent or paid documents against later contact/settings changes. Copy a document into a new draft to create a new invoice with a fresh number and public link.

Overdue means a sent invoice whose due date is before today. It is computed rather than stored as a fourth status. Dashboard amounts are separated by currency; no foreign-exchange conversion is performed. Decimal calculations round invoice amounts to two places, or zero for JPY. New exact numeric values coexist with legacy numeric columns to retain existing data.

## Verification

Use the existing environment without installing dependencies. Run pytest with `python -m pytest` so imports also work when the checkout shares the environment through a symlink.

Place temporary test databases, pytest artifacts and screenshots in a task-owned directory under `tmp/`, with a `.codex-tmp` marker, and set `TMPDIR` and `DATABASE_BACKUP_DIR` to that directory for the test run. Tests cover invoice workflows, permissions, language choices, migration, Decimal rounding and bilingual multi-page PDF output.

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider
.venv/bin/ruff check --no-cache app tests
```

The bundled Noto Sans SC font supports Chinese PDF output. Its source and OFL license are included alongside the font in `app/static/fonts/`.
