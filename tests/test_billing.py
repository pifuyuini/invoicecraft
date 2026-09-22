from conftest import signup

from app.config import settings


def test_pricing_page_anonymous(client, monkeypatch):
    monkeypatch.setattr(settings, "billing_enabled", True)
    resp = client.get("/pricing")
    assert resp.status_code == 200
    assert "Pro" in resp.text


def test_checkout_degrades_without_stripe_keys(client, monkeypatch):
    monkeypatch.setattr(settings, "billing_enabled", True)
    signup(client)
    resp = client.post("/billing/checkout", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/pricing?unavailable=1"


def test_portal_degrades_without_stripe_keys(client, monkeypatch):
    monkeypatch.setattr(settings, "billing_enabled", True)
    signup(client)
    resp = client.post("/billing/portal", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/pricing"


def test_webhook_rejected_when_unconfigured(client):
    resp = client.post("/billing/webhook", content=b"{}")
    assert resp.status_code == 400


def test_billing_success_requires_login(client):
    resp = client.get("/billing/success", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"
