from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import func, select

from ..db import SessionDep
from ..models import Client, Invoice, User
from ..security import RequiredUser
from ..templating import templates

router = APIRouter(tags=["clients"])


def _get_client(session: SessionDep, user: User, client_id: int) -> Client:
    client = session.get(Client, client_id)
    if not client or client.user_id != user.id:
        raise HTTPException(status_code=404)
    return client


def _invoice_count(session: SessionDep, client_id: int) -> int:
    return session.exec(
        select(func.count()).select_from(Invoice).where(Invoice.client_id == client_id)
    ).one()


@router.get("/clients")
def client_list(request: Request, session: SessionDep, user: RequiredUser):
    clients = list(
        session.exec(
            select(Client).where(Client.user_id == user.id).order_by(Client.name)
        ).all()
    )
    rows = [
        {"client": client, "invoice_count": _invoice_count(session, client.id)}
        for client in clients
    ]
    return templates.TemplateResponse(
        request, "clients/list.html", {"user": user, "rows": rows}
    )


@router.get("/clients/new")
def client_new(request: Request, user: RequiredUser):
    return templates.TemplateResponse(
        request, "clients/new.html", {"user": user, "error": None}
    )


@router.post("/clients")
def client_create(
    request: Request,
    session: SessionDep,
    user: RequiredUser,
    name: Annotated[str, Form()],
    email: Annotated[str, Form()] = "",
    company: Annotated[str, Form()] = "",
    address: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
):
    name = name.strip()
    if not name:
        return templates.TemplateResponse(
            request,
            "clients/new.html",
            {"user": user, "error": "Name is required."},
            status_code=400,
        )
    client = Client(
        user_id=user.id,
        name=name,
        email=email.strip(),
        company=company.strip(),
        address=address.strip(),
        notes=notes.strip(),
    )
    session.add(client)
    session.commit()
    return RedirectResponse("/clients", 303)


@router.get("/clients/{client_id}/edit")
def client_edit_form(
    request: Request, session: SessionDep, user: RequiredUser, client_id: int
):
    client = _get_client(session, user, client_id)
    return templates.TemplateResponse(
        request,
        "clients/edit.html",
        {"user": user, "client": client, "error": None},
    )


@router.post("/clients/{client_id}/edit")
def client_edit(
    request: Request,
    session: SessionDep,
    user: RequiredUser,
    client_id: int,
    name: Annotated[str, Form()],
    email: Annotated[str, Form()] = "",
    company: Annotated[str, Form()] = "",
    address: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
):
    client = _get_client(session, user, client_id)
    name = name.strip()
    if not name:
        return templates.TemplateResponse(
            request,
            "clients/edit.html",
            {"user": user, "client": client, "error": "Name is required."},
            status_code=400,
        )
    client.name = name
    client.email = email.strip()
    client.company = company.strip()
    client.address = address.strip()
    client.notes = notes.strip()
    session.add(client)
    session.commit()
    return RedirectResponse("/clients", 303)


@router.post("/clients/{client_id}/delete")
def client_delete(
    request: Request, session: SessionDep, user: RequiredUser, client_id: int
):
    client = _get_client(session, user, client_id)
    if _invoice_count(session, client.id) > 0:
        return templates.TemplateResponse(
            request,
            "clients/edit.html",
            {
                "user": user,
                "client": client,
                "error": "This client has invoices and cannot be deleted.",
            },
            status_code=400,
        )
    session.delete(client)
    session.commit()
    return RedirectResponse("/clients", 303)
