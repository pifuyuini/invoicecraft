from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select

from ..db import SessionDep
from ..models import User
from ..security import (
    CurrentUser,
    hash_password,
    login_user,
    logout_user,
    verify_password,
)
from ..templating import templates

router = APIRouter(tags=["auth"])


@router.get("/signup")
def signup_form(request: Request, user: CurrentUser):
    if user:
        return RedirectResponse("/dashboard", 303)
    return templates.TemplateResponse(request, "auth/signup.html", {"error": None})


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
    if len(password) < 8:
        error = "Password must be at least 8 characters."
    elif session.exec(select(User).where(User.email == email)).first():
        error = "This email is already registered."
    if error:
        return templates.TemplateResponse(
            request, "auth/signup.html", {"error": error}, status_code=400
        )
    user = User(email=email, name=name.strip(), hashed_password=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    login_user(request, user)
    return RedirectResponse("/dashboard", 303)


@router.get("/login")
def login_form(request: Request, user: CurrentUser):
    if user:
        return RedirectResponse("/dashboard", 303)
    return templates.TemplateResponse(request, "auth/login.html", {"error": None})


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
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": "Invalid email or password."},
            status_code=400,
        )
    login_user(request, user)
    return RedirectResponse("/dashboard", 303)


@router.post("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/", 303)
