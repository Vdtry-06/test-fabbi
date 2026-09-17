import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user, get_redis
from app.core.redis import RedisClient
from app.db.session import get_db
from app.models.todo import Todo
from app.models.user import User
from app.schemas.todo import TodoCreate, TodoListResponse, TodoResponse, TodoUpdate, TodoBulkStatusUpdate
from app.services.tag_service import get_tag_by_id
from app.services.todo_service import (
    create_todo,
    delete_todo,
    get_todo_by_id,
    get_todos,
    update_todo,
    add_tag_to_todo,
    remove_tag_from_todo,
    bulk_update_status,
    bulk_delete_todos,
)

router = APIRouter()

CACHE_TTL = 300  # 5 minutes


class DeleteBulkRequest(BaseModel):
    todo_ids: list[uuid.UUID]


def _todo_cache_key(user_id: uuid.UUID, page: int, size: int, status_filter: bool | None, tag_id: uuid.UUID | None, keyword: str | None) -> str:
    """Build a per-user, per-page cache key including filter params."""
    s = f"todos:list:{user_id}:{page}:{size}:{status_filter}:{tag_id}:{keyword}"
    return s


def _todo_cache_pattern(user_id: uuid.UUID) -> str:
    """Pattern prefix for all cache keys belonging to a user."""
    return f"todos:list:{user_id}:*"


async def _invalidate_user_todo_cache(redis: RedisClient, user_id: uuid.UUID) -> None:
    """Delete all cached todo-list pages for the given user."""
    pattern = _todo_cache_pattern(user_id)
    async for key in redis.client.scan_iter(pattern):
        await redis.delete(key)


@router.get("", response_model=TodoListResponse)
async def list_todos(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1),
    status: bool | None = Query(None, description="Filter by completion status"),
    tag_id: uuid.UUID | None = Query(None, description="Filter by tag ID"),
    keyword: str | None = Query(None, description="Filter by title keyword"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """Get paginated list of todos for the authenticated user only (with filters)."""
    skip = (page - 1) * size

    cache_key = _todo_cache_key(current_user.id, page, size, status, tag_id, keyword)

    cached = await redis.get(cache_key)
    if cached:
        cached_data = json.loads(cached)
        return TodoListResponse(**cached_data)

    todos, total = await get_todos(
        db, user_id=current_user.id, skip=skip, limit=size, status=status, tag_id=tag_id, keyword=keyword
    )

    items = [
        TodoResponse.model_validate(todo)
        for todo in todos
    ]
    
    # We populate user_email manually since we didn't join it to keep things simple
    for item in items:
        item.user_email = current_user.email

    response = TodoListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
    )

    await redis.set(cache_key, response.model_dump_json(), ex=CACHE_TTL)
    return response


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_new_todo(
    todo_data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    todo = await create_todo(db, todo_data, current_user.id)
    await _invalidate_user_todo_cache(redis, current_user.id)
    
    # Need to get with tags loaded
    todo_with_tags = await get_todo_by_id(db, todo.id)
    
    resp = TodoResponse.model_validate(todo_with_tags)
    resp.user_email = current_user.email
    return resp


@router.patch("/bulk-status", status_code=status.HTTP_200_OK)
async def bulk_status_update(
    bulk_data: TodoBulkStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
) -> Any:
    """Bulk update completed status for multiple todos."""
    count = await bulk_update_status(db, current_user.id, bulk_data.todo_ids, bulk_data.completed)
    await _invalidate_user_todo_cache(redis, current_user.id)
    return {"updated": count}


@router.delete("/bulk", status_code=status.HTTP_200_OK)
async def bulk_delete(
    bulk_data: DeleteBulkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
) -> Any:
    """Bulk delete multiple todos."""
    count = await bulk_delete_todos(db, current_user.id, bulk_data.todo_ids)
    await _invalidate_user_todo_cache(redis, current_user.id)
    return {"deleted": count}


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    if todo.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    resp = TodoResponse.model_validate(todo)
    resp.user_email = current_user.email
    return resp


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_existing_todo(
    todo_id: uuid.UUID,
    todo_data: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    if todo.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    update_data = todo_data.model_dump(exclude_unset=True)
    updated_todo = await update_todo(db, todo, update_data)
    
    # Reload with tags
    updated_todo = await get_todo_by_id(db, updated_todo.id)

    await _invalidate_user_todo_cache(redis, current_user.id)

    resp = TodoResponse.model_validate(updated_todo)
    resp.user_email = current_user.email
    return resp


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_todo(
    todo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    if todo.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await delete_todo(db, todo)
    await _invalidate_user_todo_cache(redis, current_user.id)
    return None


@router.post("/{todo_id}/tags/{tag_id}", response_model=TodoResponse)
async def add_tag(
    todo_id: uuid.UUID,
    tag_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    todo = await get_todo_by_id(db, todo_id)
    tag = await get_tag_by_id(db, tag_id)
    
    if not todo or not tag:
        raise HTTPException(status_code=404, detail="Todo or Tag not found")
    if todo.user_id != current_user.id or tag.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    todo_with_tags = await add_tag_to_todo(db, todo, tag)
    await _invalidate_user_todo_cache(redis, current_user.id)
    
    resp = TodoResponse.model_validate(todo_with_tags)
    resp.user_email = current_user.email
    return resp


@router.delete("/{todo_id}/tags/{tag_id}", response_model=TodoResponse)
async def remove_tag(
    todo_id: uuid.UUID,
    tag_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    todo = await get_todo_by_id(db, todo_id)
    tag = await get_tag_by_id(db, tag_id)
    
    if not todo or not tag:
        raise HTTPException(status_code=404, detail="Todo or Tag not found")
    if todo.user_id != current_user.id or tag.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    todo_with_tags = await remove_tag_from_todo(db, todo, tag)
    await _invalidate_user_todo_cache(redis, current_user.id)
    
    resp = TodoResponse.model_validate(todo_with_tags)
    resp.user_email = current_user.email
    return resp