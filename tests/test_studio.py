"""Behavior-level regression coverage for the studio workflow."""

from urllib.parse import urlencode

from conftest import signup


def create_customer(client, name="山川设计", email="studio@example.com"):
    response = client.post(
        "/clients",
        data={
            "name": name,
            "email": email,
            "company": "山川工作室",
            "address": "上海市静安区",
        },
        headers={"accept": "application/json"},
    )
    assert response.status_code in (200, 201), response.text
    return response.json()["id"]


def fields(customer=None, currency="USD", **updates):
    values = {
        "client_id": str(customer or ""),
        "currency": currency,
        "tax_rate": "10",
        "issue_date": "2026-09-22",
        "due_date": "2026-10-22",
        "description": "Brand design 品牌设计",
        "quantity": "2",
        "unit_price": "150.25",
        "notes": "A note to preserve",
        "document_language": "en",
    }
    values.update(updates)
    return values


def submit(client, endpoint="/invoices", values=None):
    return client.post(
        endpoint,
        content=urlencode(values or fields()),
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )


def create_invoice(client, customer=None, **updates):
    response = submit(client, values=fields(customer, **updates))
    assert response.status_code == 303, response.text
    return response.headers["location"].split("?")[0]


def test_no_five_invoice_limit_when_billing_disabled(client):
    signup(client)
    for _ in range(7):
        create_invoice(client)


def test_number_never_reused_after_deletion(client):
    signup(client)
    first = create_invoice(client)
    second = create_invoice(client)
    assert "INV-0002" in client.get(second).text
    assert client.post(second + "/delete", follow_redirects=False).status_code == 303
    third = create_invoice(client)
    assert "INV-0003" in client.get(third).text
    assert "INV-0001" in client.get(first).text


def test_copy_makes_new_draft_and_keeps_source(client):
    signup(client)
    original = create_invoice(client)
    client.post(original + "/status", data={"status": "paid"})
    response = client.post(original + "/duplicate", follow_redirects=False)
    assert response.status_code == 303, response.text
    target = response.headers["location"].split("?")[0]
    assert target != original
    copied = client.get(target)
    assert copied.status_code == 200
    assert "INV-0002" in copied.text
    assert "Brand design" in copied.text
    assert client.get(original).status_code == 200


def test_sent_document_keeps_customer_snapshot(client):
    signup(client)
    customer = create_customer(client, "Original Studio")
    invoice = create_invoice(client, customer)
    client.post(invoice + "/status", data={"status": "sent"})
    client.post(
        f"/clients/{customer}/edit",
        data={"name": "Renamed Studio", "email": "new@example.com"},
    )
    page = client.get(invoice)
    assert "Original Studio" in page.text
    assert "Renamed Studio" not in page.text


def test_preview_is_read_only_and_server_rounded(client):
    signup(client)
    preview = submit(
        client,
        "/invoices/preview",
        fields(currency="JPY", tax_rate="0", quantity="1", unit_price="100.5"),
    )
    assert preview.status_code == 200, preview.text
    payload = preview.json()
    assert "html" in payload
    assert str(payload["totals"]["total"]) in ("101", "101.0", "101.00")
    invoice = create_invoice(client)
    assert "INV-0001" in client.get(invoice).text


def test_invalid_amount_does_not_silently_save(client):
    signup(client)
    for price in ("-1", "nan", "inf", "not-a-number"):
        response = submit(client, values=fields(unit_price=price))
        assert response.status_code in (400, 422), response.text
        assert "A note to preserve" in response.text
    invoice = create_invoice(client)
    assert "INV-0001" in client.get(invoice).text


def test_invoice_search_filters_and_client_detail(client):
    signup(client)
    first = create_customer(client, "Northstar")
    second = create_customer(client, "Evergreen")
    create_invoice(client, first, currency="USD")
    create_invoice(client, second, currency="EUR")
    page = client.get("/invoices?q=Northstar&currency=USD")
    assert page.status_code == 200
    assert "INV-0001" in page.text
    assert "INV-0002" not in page.text
    assert client.get(f"/clients/{first}").status_code == 200


def test_cross_user_cannot_duplicate_or_view_client(client):
    signup(client, email="owner@example.com")
    customer = create_customer(client)
    invoice = create_invoice(client, customer)
    client.post("/logout")
    signup(client, email="other@example.com")
    assert (
        client.post(invoice + "/duplicate", follow_redirects=False).status_code == 404
    )
    assert client.get(f"/clients/{customer}").status_code == 404


def test_language_switch_and_document_language_independent(client):
    signup(client)
    invoice = create_invoice(client, document_language="en")
    response = client.post("/language", json={"language": "zh-CN"})
    assert response.status_code == 200
    assert "账单" in client.get("/invoices").text
    assert 'class="invoice-document" lang="en"' in client.get(invoice).text
    assert "Bill to" in client.get(invoice).text
    response = client.post("/language", json={"language": "en"})
    assert response.status_code == 200
    assert "Invoices" in client.get("/invoices").text


def test_settings_and_sent_issuer_snapshot(client):
    signup(client)
    settings = {
        "issuer_name": "Original Issuer",
        "issuer_email": "hello@example.com",
        "issuer_address": "上海",
        "payment_instructions": "Original payment instructions",
        "default_currency": "CNY",
        "default_tax_rate": "6",
        "language": "en",
        "document_language": "zh-CN",
    }
    assert (
        client.post("/settings", data=settings, follow_redirects=False).status_code
        == 303
    )
    invoice = create_invoice(client)
    client.post(invoice + "/status", data={"status": "sent"})
    settings.update(
        issuer_name="New Issuer", payment_instructions="New payment instructions"
    )
    assert (
        client.post("/settings", data=settings, follow_redirects=False).status_code
        == 303
    )
    page = client.get(invoice).text
    assert "Original Issuer" in page and "Original payment instructions" in page
    assert "New Issuer" not in page and "New payment instructions" not in page
    new_page = client.get("/invoices/new").text
    assert "selected>CNY" in new_page or "CNY selected" in new_page


def test_pagination_and_per_currency_totals(client):
    signup(client)
    for _ in range(26):
        create_invoice(
            client, currency="USD", quantity="1", unit_price="10", tax_rate="0"
        )
    first_page = client.get("/invoices").text
    second_page = client.get("/invoices?page=2").text
    assert "INV-0026" in first_page and "INV-0001" not in first_page
    assert "INV-0001" in second_page and "INV-0026" not in second_page
    usd = create_invoice(
        client, currency="USD", quantity="1", unit_price="11.25", tax_rate="0"
    )
    eur = create_invoice(
        client, currency="EUR", quantity="1", unit_price="22.50", tax_rate="0"
    )
    client.post(usd + "/status", data={"status": "sent"})
    client.post(eur + "/status", data={"status": "sent"})
    overview = client.get("/dashboard").text
    assert "$11.25" in overview and "€22.50" in overview
    assert "$33.75" not in overview


def test_public_document_keeps_its_language(client):
    import re

    signup(client)
    invoice = create_invoice(client, document_language="zh-CN")
    token = re.search(r"/i/([A-Za-z0-9_-]+)", client.get(invoice).text).group(1)
    client.post("/logout")
    client.post("/language", json={"language": "en"})
    public = client.get(f"/i/{token}")
    assert public.status_code == 200
    assert 'class="invoice-document" lang="zh-CN"' in public.text
    assert "开票方" in public.text
