from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.removeprefix("sqlite:///")
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(settings.database_url)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
