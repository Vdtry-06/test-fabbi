import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Table, Column, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.todo import Todo
    from app.models.user import User

# Association table for Todo <-> Tag (Many-to-Many)
todo_tags = Table(
    "todo_tags",
    Base.metadata,
    Column("todo_id", ForeignKey("todos.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

class Tag(Base):
    """Tag model."""

    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    color: Mapped[str] = mapped_column(
        String(7),  # Hex color code like #FFFFFF
        default="#E2E8F0",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Prevent duplicate tag names for the same user
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_tag_name_per_user"),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="tags",
        lazy="select",
    )
    
    todos: Mapped[list["Todo"]] = relationship(
        "Todo",
        secondary=todo_tags,
        back_populates="tags",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"