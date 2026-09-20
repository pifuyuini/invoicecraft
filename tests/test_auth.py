from conftest import signup


def test_dashboard_requires_login(client):
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_signup_and_dashboard(client):
    resp = signup(client)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"
    assert client.get("/dashboard").status_code == 200


def test_signup_duplicate_email_rejected(client):
    assert signup(client).status_code == 303
    resp = signup(client)
    assert resp.status_code == 400
    assert "already registered" in resp.text


def test_signup_short_password_rejected(client):
    resp = signup(client, password="short")
    assert resp.status_code == 400


def test_login_wrong_password_rejected(client):
    signup(client)
    client.post("/logout", follow_redirects=False)
    resp = client.post(
        "/login",
        data={"email": "user@example.com", "password": "wrong-password"},
        follow_redirects=False,
    )
    assert resp.status_code == 400


def test_login_success(client):
    signup(client)
    client.post("/logout", follow_redirects=False)
    resp = client.post(
        "/login",
        data={"email": "user@example.com", "password": "password123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"
