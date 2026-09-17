import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.tag import TagResponse


class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    completed: bool = False


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    completed: bool | None = None


class TodoBulkStatusUpdate(BaseModel):
    todo_ids: list[uuid.UUID]
    completed: bool


class TodoResponse(TodoBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    user_email: str | None = None
    tags: list[TagResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TodoListResponse(BaseModel):
    items: list[TodoResponse]
    total: int
    page: int
    size: int
