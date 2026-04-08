from enum import Enum
from typing import Optional

from pydantic import field_validator
from sqlmodel import Field, SQLModel


class Category(str, Enum):
    coding = "coding"
    writing = "writing"
    debugging = "debugging"
    learning = "learning"
    other = "other"


class PromptBase(SQLModel):
    title: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1)
    model: str = Field(min_length=1, max_length=50)
    category: Category
    task_type: str = Field(min_length=1, max_length=100)
    effectiveness: int = Field(ge=1, le=5)
    tags: str = Field(default="")
    notes: Optional[str] = Field(default=None)
    token_count: Optional[int] = Field(default=None, ge=1)
    version: int = Field(default=1, ge=1)


class Prompt(PromptBase, table=True):
    __tablename__ = "prompts"

    id: Optional[int] = Field(default=None, primary_key=True)


class PromptCreate(PromptBase):
    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: str) -> str:
        """Lowercase and strip whitespace from each tag."""
        return ",".join(tag.strip().lower() for tag in v.split(",") if tag.strip())

    @field_validator("title")
    @classmethod
    def normalize_title(cls, v: str) -> str:
        return v.strip()


class PromptRead(PromptBase):
    id: int


class PromptUpdate(SQLModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    text: Optional[str] = Field(default=None, min_length=1)
    model: Optional[str] = Field(default=None, min_length=1, max_length=50)
    category: Optional[Category] = None
    task_type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    effectiveness: Optional[int] = Field(default=None, ge=1, le=5)
    tags: Optional[str] = None
    notes: Optional[str] = None
    token_count: Optional[int] = Field(default=None, ge=1)
    version: Optional[int] = Field(default=None, ge=1)
