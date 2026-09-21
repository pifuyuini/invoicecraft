from fastapi import Request

SESSION_KEY = "_flashes"


def flash(request: Request, message: str, kind: str = "success") -> None:
    flashes = list(request.session.get(SESSION_KEY, []))
    flashes.append([kind, message])
    request.session[SESSION_KEY] = flashes


def pop_flashes(request: Request) -> list[tuple[str, str]]:
    raw = request.session.pop(SESSION_KEY, [])
    return [(kind, message) for kind, message in raw]
