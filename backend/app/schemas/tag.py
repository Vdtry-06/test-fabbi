import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#E2E8F0", min_length=7, max_length=7)

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    color: str | None = Field(None, min_length=7, max_length=7)

class TagResponse(TagBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True