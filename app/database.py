from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

_url = get_settings().database_url
_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}
engine = create_engine(_url, connect_args=_args)


def init_db() -> None:
    from app import models  # noqa: F401  (registra as tabelas)

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """Injeção de dependência: uma sessão por request."""
    with Session(engine) as session:
        yield session
