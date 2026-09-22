import re
from urllib.parse import urlencode

from conftest import signup

from app.config import settings

INVOICE_FORM = [
    ("client_id", "1"),
    ("currency", "USD"),
    ("tax_rate", "10"),
    ("issue_date", "2026-09-20"),
    ("due_date", "2026-10-20"),
    ("description", "Design"),
    ("quantity", "2"),
    ("unit_price", "150"),
    ("description", "Hosting"),
    ("quantity", "1"),
    ("unit_price", "25"),
]


def make_client(client, name="Acme"):
    return client.post(
        "/clients",
        data={"name": name, "email": "a@acme.co", "company": "Acme Inc"},
        follow_redirects=False,
    )


def post_form(client, url, fields):
    # httpx 0.28 no longer form-encodes a list of tuples; encode explicitly.
    return client.post(
        url,
        content=urlencode(fields),
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )


def make_invoice(client, form=None):
    return post_form(client, "/invoices", form or INVOICE_FORM)


def test_full_invoice_flow(client):
    signup(client)
    assert make_client(client).status_code == 303

    resp = make_invoice(client)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/invoices/1"

    detail = client.get("/invoices/1")
    assert "INV-0001" in detail.text
    assert "357.50" in detail.text  # (2*150 + 1*25) * 1.1

    listing = client.get("/invoices")
    assert "INV-0001" in listing.text
    assert "Acme" in listing.text


def test_invoice_pdf_and_public_link(client):
    signup(client)
    make_client(client)
    make_invoice(client)

    pdf = client.get("/invoices/1/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    detail = client.get("/invoices/1").text
    token = re.search(r"/i/([A-Za-z0-9_-]+)", detail).group(1)
    assert client.get(f"/i/{token}").status_code == 200
    assert client.get("/i/does-not-exist").status_code == 404


def test_invoice_ownership_enforced(client):
    signup(client, email="owner@example.com")
    make_client(client)
    make_invoice(client)
    client.post("/logout", follow_redirects=False)

    signup(client, email="intruder@example.com")
    assert client.get("/invoices/1").status_code == 404
    assert client.get("/clients/1/edit").status_code == 404


def test_free_limit_blocks_creation(client, monkeypatch):
    monkeypatch.setattr(settings, "free_invoice_limit", 1)
    monkeypatch.setattr(settings, "billing_enabled", True)
    signup(client)
    make_client(client)
    assert make_invoice(client).status_code == 303
    resp = make_invoice(client)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/pricing?limit=1"


def test_invoice_status_filter(client):
    signup(client)
    make_client(client)
    make_invoice(client)
    client.post("/invoices/1/status", data={"status": "sent"})

    assert "INV-0001" in client.get("/invoices?status=sent").text
    assert "INV-0001" not in client.get("/invoices?status=paid").text
    assert "INV-0001" in client.get("/invoices").text


def test_invoice_requires_at_least_one_item(client):
    signup(client)
    resp = post_form(
        client,
        "/invoices",
        [("currency", "USD"), ("tax_rate", "0"), ("issue_date", "2026-09-20")],
    )
    assert resp.status_code == 400
