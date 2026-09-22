from math import ceil

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel import select

from ..db import SessionDep
from ..flash import flash
from ..models import Client, Invoice
from ..security import RequiredUser
from ..services.invoicing import client_data, invoice_rows, summarize
from ..templating import render

router = APIRouter(tags=["clients"])


def _get_client(session, user, client_id):
    client = session.get(Client, client_id)
    if not client or client.user_id != user.id:
        raise HTTPException(status_code=404)
    return client


def _invoices(session, client):
    return list(
        session.exec(
            select(Invoice)
            .where(Invoice.client_id == client.id, Invoice.user_id == client.user_id)
            .order_by(Invoice.id.desc())
        ).all()
    )


def _parse_client(raw):
    form = {
        key: str(raw.get(key, "")).strip()
        for key in ("name", "email", "company", "address", "notes")
    }
    errors = {}
    if not form["name"]:
        errors["name"] = "Name is required."
    if form["email"] and ("@" not in form["email"] or " " in form["email"]):
        errors["email"] = "Enter a valid email address."
    return form, errors


@router.get("/clients")
def client_list(
    request: Request,
    session: SessionDep,
    user: RequiredUser,
    q: str = "",
    page: int = 1,
):
    clients = list(
        session.exec(
            select(Client).where(Client.user_id == user.id).order_by(Client.name)
        ).all()
    )
    if q.strip():
        needle = q.strip().casefold()
        clients = [
            client
            for client in clients
            if any(
                needle in value.casefold()
                for value in (client.name, client.company, client.email)
            )
        ]
    total = len(clients)
    pages = max(1, ceil(total / 25))
    page = max(1, min(page, pages))
    rows = [
        {"client": client, "invoice_count": len(_invoices(session, client))}
        for client in clients[(page - 1) * 25 : page * 25]
    ]
    return render(
        request,
        "clients/list.html",
        {
            "user": user,
            "rows": rows,
            "q": q,
            "page": page,
            "pages": pages,
            "total": total,
        },
    )


@router.get("/clients/new")
def client_new(request: Request, user: RequiredUser):
    return render(
        request, "clients/new.html", {"user": user, "form": {}, "client": None}
    )


@router.post("/clients")
async def client_create(request: Request, session: SessionDep, user: RequiredUser):
    json_input = "application/json" in request.headers.get("content-type", "")
    raw = await request.json() if json_input else await request.form()
    wants_json = json_input or "application/json" in request.headers.get("accept", "")
    form, errors = _parse_client(raw)
    if errors:
        if wants_json:
            return JSONResponse({"errors": errors}, status_code=400)
        return render(
            request,
            "clients/new.html",
            {
                "user": user,
                "client": None,
                "form": form,
                "errors": errors,
                "error": next(iter(errors.values())),
            },
            status_code=400,
        )
    client = Client(user_id=user.id, **form)
    session.add(client)
    session.commit()
    session.refresh(client)
    if wants_json:
        return {"id": client.id, "client": {"id": client.id, **client_data(client)}}
    flash(request, "Client saved.")
    return RedirectResponse(f"/clients/{client.id}", 303)


@router.get("/clients/{client_id}")
def client_detail(
    request: Request, session: SessionDep, user: RequiredUser, client_id: int
):
    client = _get_client(session, user, client_id)
    rows = invoice_rows(session, _invoices(session, client))
    return render(
        request,
        "clients/detail.html",
        {"user": user, "client": client, "rows": rows, "summaries": summarize(rows)},
    )


@router.get("/clients/{client_id}/edit")
def client_edit_form(
    request: Request, session: SessionDep, user: RequiredUser, client_id: int
):
    client = _get_client(session, user, client_id)
    return render(
        request,
        "clients/edit.html",
        {
            "user": user,
            "client": client,
            "form": {
                key: getattr(client, key)
                for key in ("name", "email", "company", "address", "notes")
            },
        },
    )


@router.post("/clients/{client_id}/edit")
async def client_edit(
    request: Request, session: SessionDep, user: RequiredUser, client_id: int
):
    client = _get_client(session, user, client_id)
    form, errors = _parse_client(await request.form())
    if errors:
        return render(
            request,
            "clients/edit.html",
            {
                "user": user,
                "client": client,
                "form": form,
                "errors": errors,
                "error": next(iter(errors.values())),
            },
            status_code=400,
        )
    for key, value in form.items():
        setattr(client, key, value)
    session.add(client)
    session.commit()
    flash(request, "Client saved.")
    return RedirectResponse(f"/clients/{client.id}", 303)


@router.post("/clients/{client_id}/delete")
def client_delete(
    request: Request, session: SessionDep, user: RequiredUser, client_id: int
):
    client = _get_client(session, user, client_id)
    if _invoices(session, client):
        message = "This client has invoices and cannot be deleted."
        return render(
            request,
            "clients/edit.html",
            {
                "user": user,
                "client": client,
                "form": {
                    key: getattr(client, key)
                    for key in ("name", "email", "company", "address", "notes")
                },
                "error": message,
            },
            status_code=400,
        )
    session.delete(client)
    session.commit()
    flash(request, "Client deleted.", "info")
    return RedirectResponse("/clients", 303)
