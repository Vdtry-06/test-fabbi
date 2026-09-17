import uuid
from typing import Sequence

from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.todo import Todo
from app.models.tag import Tag
from app.schemas.todo import TodoCreate


async def create_todo(
    db: AsyncSession, todo_data: TodoCreate, user_id: uuid.UUID
) -> Todo:
    todo = Todo(
        title=todo_data.title,
        description=todo_data.description,
        user_id=user_id,
    )
    db.add(todo)
    await db.flush()
    await db.refresh(todo)
    return todo


async def get_todos(
    db: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
    status: bool | None = None,
    tag_id: uuid.UUID | None = None,
    keyword: str | None = None,
) -> tuple[list[Todo], int]:
    """Get all todos with pagination and filtering."""
    base_query = select(Todo).where(Todo.user_id == user_id)
    count_query = select(func.count()).select_from(Todo).where(Todo.user_id == user_id)

    if status is not None:
        base_query = base_query.where(Todo.completed == status)
        count_query = count_query.where(Todo.completed == status)
    
    if tag_id is not None:
        base_query = base_query.where(Todo.tags.any(Tag.id == tag_id))
        count_query = count_query.where(Todo.tags.any(Tag.id == tag_id))

    if keyword:
        base_query = base_query.where(Todo.title.ilike(f"%{keyword}%"))
        count_query = count_query.where(Todo.title.ilike(f"%{keyword}%"))

    # Load tags along with todos
    query = base_query.options(selectinload(Todo.tags)).order_by(Todo.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    todos = list(result.scalars().all())

    total = await db.execute(count_query)

    return todos, total.scalar_one()


async def get_todo_by_id(db: AsyncSession, todo_id: uuid.UUID) -> Todo | None:
    result = await db.execute(select(Todo).options(selectinload(Todo.tags)).where(Todo.id == todo_id))
    return result.scalar_one_or_none()


async def update_todo(db: AsyncSession, todo: Todo, update_data: dict) -> Todo:
    for key, value in update_data.items():
        setattr(todo, key, value)
    await db.flush()
    await db.refresh(todo)
    return todo


async def delete_todo(db: AsyncSession, todo: Todo) -> None:
    await db.delete(todo)
    await db.flush()


# --- Tier 4 Extensions ---

async def add_tag_to_todo(db: AsyncSession, todo: Todo, tag: Tag) -> Todo:
    if tag not in todo.tags:
        todo.tags.append(tag)
        await db.commit()
        await db.refresh(todo)
    return todo


async def remove_tag_from_todo(db: AsyncSession, todo: Todo, tag: Tag) -> Todo:
    if tag in todo.tags:
        todo.tags.remove(tag)
        await db.commit()
        await db.refresh(todo)
    return todo


async def bulk_update_status(db: AsyncSession, user_id: uuid.UUID, todo_ids: list[uuid.UUID], completed: bool) -> int:
    stmt = (
        update(Todo)
        .where(Todo.id.in_(todo_ids), Todo.user_id == user_id)
        .values(completed=completed)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def bulk_delete_todos(db: AsyncSession, user_id: uuid.UUID, todo_ids: list[uuid.UUID]) -> int:
    stmt = (
        delete(Todo)
        .where(Todo.id.in_(todo_ids), Todo.user_id == user_id)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount

