import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.tag import TagCreate, TagResponse, TagUpdate
from app.services import tag_service

router = APIRouter()


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    *,
    db: AsyncSession = Depends(get_db),
    tag_in: TagCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Create a new tag."""
    tag = await tag_service.create_tag(db, tag_in, current_user.id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists",
        )
    return tag


@router.get("", response_model=list[TagResponse])
async def get_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Retrieve all tags for current user."""
    tags = await tag_service.get_tags_by_user(db, current_user.id)
    return tags


@router.put("/{id}", response_model=TagResponse)
async def update_tag(
    *,
    db: AsyncSession = Depends(get_db),
    id: uuid.UUID,
    tag_in: TagUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update a tag."""
    tag = await tag_service.get_tag_by_id(db, id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if tag.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    updated_tag = await tag_service.update_tag(db, tag, tag_in)
    if not updated_tag:
        raise HTTPException(status_code=400, detail="Tag name already exists")
    return updated_tag


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    *,
    db: AsyncSession = Depends(get_db),
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Delete a tag."""
    tag = await tag_service.get_tag_by_id(db, id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if tag.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    await tag_service.delete_tag(db, tag)