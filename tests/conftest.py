import os
import tempfile

_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.db import engine
from app.main import app


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with TestClient(app) as c:
        c.post("/language", json={"language": "en"})
        yield c


def signup(client, email="user@example.com", password="password123", name="User"):
    return client.post(
        "/signup",
        data={"email": email, "password": password, "name": name},
        follow_redirects=False,
    )
