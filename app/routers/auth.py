from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select

from ..db import SessionDep
from ..flash import flash
from ..models import User
from ..security import (
    CurrentUser,
    hash_password,
    login_user,
    logout_user,
    verify_password,
)
from ..templating import render

router = APIRouter(tags=["auth"])


@router.get("/signup")
def signup_form(request: Request, user: CurrentUser):
    if user:
        return RedirectResponse("/dashboard", 303)
    return render(request, "auth/signup.html", {"error": None})


@router.post("/signup")
def signup(
    request: Request,
    session: SessionDep,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    name: Annotated[str, Form()] = "",
):
    email = email.strip().lower()
    error = None
    if "@" not in email or " " in email:
        error = "Enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif session.exec(select(User).where(User.email == email)).first():
        error = "This email is already registered."
    if error:
        return render(
            request,
            "auth/signup.html",
            {"error": error, "form": {"email": email, "name": name}},
            status_code=400,
        )
    language = request.session.get("language", "zh-CN")
    user = User(
        email=email,
        name=name.strip(),
        hashed_password=hash_password(password),
        language=language,
        document_language=language,
        issuer_name=name.strip(),
        issuer_email=email,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    login_user(request, user)
    flash(request, "Welcome to InvoiceCraft! Create your first invoice.")
    return RedirectResponse("/dashboard", 303)


@router.get("/login")
def login_form(request: Request, user: CurrentUser):
    if user:
        return RedirectResponse("/dashboard", 303)
    return render(request, "auth/login.html", {"error": None})


@router.post("/login")
def login(
    request: Request,
    session: SessionDep,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    email = email.strip().lower()
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.hashed_password):
        return render(
            request,
            "auth/login.html",
            {"error": "Invalid email or password.", "form": {"email": email}},
            status_code=400,
        )
    login_user(request, user)
    flash(request, "Welcome back!")
    return RedirectResponse("/dashboard", 303)


@router.post("/logout")
def logout(request: Request):
    logout_user(request)
    flash(request, "You've been logged out.", "info")
    return RedirectResponse("/", 303)
