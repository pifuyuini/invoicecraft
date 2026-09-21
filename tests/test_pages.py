def test_terms_page(client):
    resp = client.get("/terms")
    assert resp.status_code == 200
    assert "Terms of Service" in resp.text


def test_privacy_page(client):
    resp = client.get("/privacy")
    assert resp.status_code == 200
    assert "Privacy Policy" in resp.text


def test_404_page_is_branded_html(client):
    resp = client.get("/no-such-page")
    assert resp.status_code == 404
    assert "Page not found" in resp.text
    assert 'href="/terms"' in resp.text


def test_security_headers_present(client):
    resp = client.get("/")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" in resp.headers


def test_footer_links_present(client):
    resp = client.get("/")
    assert 'href="/terms"' in resp.text
    assert 'href="/privacy"' in resp.text
