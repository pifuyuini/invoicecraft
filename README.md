# InvoiceCraft

Professional invoices in minutes. A self-hosted micro-SaaS for freelancers and small
businesses: create invoices, manage clients, download PDFs, share public payment links —
with a built-in free tier and a Stripe-powered Pro subscription.

## Features

- **Invoice management** — line items, tax rate, multi-currency (USD/EUR/GBP/CNY/JPY), draft → sent → paid status tracking
- **One-click PDF** — clean, print-ready invoice PDFs
- **Public share links** — every invoice gets a private, no-login URL for clients
- **Client management** — reusable client records
- **Dashboard** — outstanding/paid totals and recent activity at a glance
- **Monetization built in** — free plan (5 invoices) + Pro plan ($6/month) via Stripe Checkout & webhooks

## Tech stack

FastAPI · SQLModel (SQLite by default) · Jinja2 server-rendered UI · fpdf2 · Stripe

## Quick start (local)

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Open http://localhost:8000 — sign up and create your first invoice.

## Configuration

All settings come from environment variables (or a `.env` file, which is git-ignored):

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | dev value | **Set a long random value in production** (signs session cookies) |
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLAlchemy database URL |
| `BASE_URL` | `http://localhost:8000` | Public URL of the deployment (used in share/checkout links) |
| `FREE_INVOICE_LIMIT` | `5` | Invoices a free account may create |
| `STRIPE_SECRET_KEY` | _empty_ | Stripe API secret; billing is disabled while empty |
| `PRO_PRICE_MONTHLY_ID` | _empty_ | Stripe Price ID for the Pro monthly plan |
| `STRIPE_WEBHOOK_SECRET` | _empty_ | Signing secret for `/billing/webhook` |

Without Stripe keys the app runs normally and the pricing page shows "payments
launching soon" — nothing breaks.

## Tests

```bash
uv run pytest
```

## Deployment

A production-ready `Dockerfile` is included. See [LAUNCH.md](LAUNCH.md) for the
complete go-to-market guide (Stripe setup, deploy steps, verification checklist).
