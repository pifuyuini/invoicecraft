from typing import Annotated

from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash

from .db import SessionDep
from .flash import flash
from .models import User

password_hash = PasswordHash.recommended()

SESSION_KEY = "user_id"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def login_user(request: Request, user: User) -> None:
    request.session[SESSION_KEY] = user.id


def logout_user(request: Request) -> None:
    request.session.clear()


def get_current_user(request: Request, session: SessionDep) -> User | None:
    user_id = request.session.get(SESSION_KEY)
    if user_id is None:
        return None
    return session.get(User, user_id)


CurrentUser = Annotated[User | None, Depends(get_current_user)]


def require_user(request: Request, user: CurrentUser) -> User:
    if user is None:
        flash(request, "Please log in to continue.", "info")
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


RequiredUser = Annotated[User, Depends(require_user)]
