import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user, get_redis
from app.core.redis import RedisClient
from app.db.session import get_db
from app.models.todo import Todo
from app.models.user import User
from app.schemas.todo import TodoCreate, TodoListResponse, TodoResponse, TodoUpdate
from app.services.todo_service import (
    create_todo,
    delete_todo,
    get_todo_by_id,
    get_todos,
    update_todo,
)

router = APIRouter()

CACHE_TTL = 300  # 5 minutes


def _todo_cache_key(user_id: uuid.UUID, page: int, size: int) -> str:
    """Build a per-user, per-page cache key to prevent cross-user data leaks (B2, B12)."""
    return f"todos:list:{user_id}:{page}:{size}"


def _todo_cache_pattern(user_id: uuid.UUID) -> str:
    """Pattern prefix for all cache keys belonging to a user."""
    return f"todos:list:{user_id}:*"


async def _invalidate_user_todo_cache(redis: RedisClient, user_id: uuid.UUID) -> None:
    """Delete all cached todo-list pages for the given user (B7, B8)."""
    # redis.client is the raw aioredis connection which supports SCAN
    pattern = _todo_cache_pattern(user_id)
    async for key in redis.client.scan_iter(pattern):
        await redis.delete(key)


@router.get("", response_model=TodoListResponse)
async def list_todos(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """Get paginated list of todos for the authenticated user only."""
    skip = (page - 1) * size

    # B2/B12 fix: cache key scoped per user + pagination params
    cache_key = _todo_cache_key(current_user.id, page, size)

    # Try to get from cache
    cached = await redis.get(cache_key)
    if cached:
        cached_data = json.loads(cached)
        return TodoListResponse(**cached_data)

    # B11 fix: use joinedload to avoid N+1 queries when fetching user email
    todos, total = await get_todos(
        db, user_id=current_user.id, skip=skip, limit=size
    )

    items = [
        TodoResponse(
            id=todo.id,
            title=todo.title,
            description=todo.description,
            completed=todo.completed,
            user_id=todo.user_id,
            created_at=todo.created_at,
            updated_at=todo.updated_at,
            user_email=current_user.email,  # B11 fix: already known from auth
        )
        for todo in todos
    ]

    response = TodoListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
    )

    # Cache the response with scoped key
    await redis.set(cache_key, response.model_dump_json(), ex=CACHE_TTL)

    return response


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_new_todo(
    todo_data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """Create a new todo item and invalidate the user's todo cache (B7)."""
    todo = await create_todo(db, todo_data, current_user.id)

    # B7 fix: invalidate all cached pages for this user after creation
    await _invalidate_user_todo_cache(redis, current_user.id)

    return TodoResponse(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        user_id=todo.user_id,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        user_email=current_user.email,
    )


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific todo by ID — only if it belongs to the current user (B3)."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )

    # B3 fix: enforce ownership
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return TodoResponse(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        user_id=todo.user_id,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        user_email=current_user.email,
    )


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_existing_todo(
    todo_id: uuid.UUID,
    todo_data: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """Update a todo item — only if it belongs to the current user (B4)."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )

    # B4 fix: enforce ownership
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # B6 fix: use `is not None` so that completed=False is properly applied
    update_data = todo_data.model_dump(exclude_unset=True)

    updated_todo = await update_todo(db, todo, update_data)

    # Invalidate cache after update
    await _invalidate_user_todo_cache(redis, current_user.id)

    return TodoResponse(
        id=updated_todo.id,
        title=updated_todo.title,
        description=updated_todo.description,
        completed=updated_todo.completed,
        user_id=updated_todo.user_id,
        created_at=updated_todo.created_at,
        updated_at=updated_todo.updated_at,
        user_email=current_user.email,
    )


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_todo(
    todo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """Delete a todo item — only if it belongs to the current user (B5)."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )

    # B5 fix: enforce ownership
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    await delete_todo(db, todo)

    # B8 fix: invalidate all cached pages for this user after deletion
    await _invalidate_user_todo_cache(redis, current_user.id)

    return None

