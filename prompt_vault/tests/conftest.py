from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from prompt_vault.app import models  # noqa: F401
from prompt_vault.app.database import get_session
from prompt_vault.app.main import _require_editor, app


@pytest.fixture(name="engine")
def engine_fixture(tmp_path):
    test_db = tmp_path / "test.db"
    test_engine = create_engine(
        f"sqlite:///{test_db}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    def get_session_override() -> Generator[Session, None, None]:
        yield session

    # Bypass JWT auth so CRUD tests focus on business logic, not auth
    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[_require_editor] = lambda: {"sub": "test", "roles": ["editor"]}
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
