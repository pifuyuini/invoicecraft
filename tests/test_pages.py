def test_terms_page(client):
    resp = client.get("/terms")
    assert resp.status_code == 200
    assert "Terms of Service" in resp.text


def test_privacy_page(client):
    resp = client.get("/privacy")
    assert resp.status_code == 200
    assert "Privacy Policy" in resp.text


def test_footer_links_present(client):
    resp = client.get("/")
    assert 'href="/terms"' in resp.text
    assert 'href="/privacy"' in resp.text
