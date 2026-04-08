from typing import Optional

from sqlmodel import Session, select

from .models import Prompt, PromptCreate, PromptUpdate


class PromptRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, *, skip: int = 0, limit: int = 100) -> list[Prompt]:
        statement = select(Prompt).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def create(self, payload: PromptCreate) -> Prompt:
        record = Prompt.model_validate(payload)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get(self, prompt_id: int) -> Optional[Prompt]:
        return self.session.get(Prompt, prompt_id)

    def update(self, prompt_id: int, payload: PromptUpdate) -> Optional[Prompt]:
        record = self.get(prompt_id)
        if record is None:
            return None
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(record, key, value)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def delete(self, prompt_id: int) -> bool:
        record = self.get(prompt_id)
        if record is None:
            return False
        self.session.delete(record)
        self.session.commit()
        return True
