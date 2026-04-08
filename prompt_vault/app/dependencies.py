from typing import Annotated

from fastapi import Depends

from .database import SessionDep
from .repository import PromptRepository


def get_repository(session: SessionDep) -> PromptRepository:
    return PromptRepository(session)


RepositoryDep = Annotated[PromptRepository, Depends(get_repository)]
