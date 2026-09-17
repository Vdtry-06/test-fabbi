import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagUpdate


async def create_tag(db: AsyncSession, tag_data: TagCreate, user_id: uuid.UUID) -> Tag | None:
    tag = Tag(
        name=tag_data.name,
        color=tag_data.color,
        user_id=user_id,
    )
    db.add(tag)
    try:
        await db.commit()
        await db.refresh(tag)
        return tag
    except IntegrityError:
        await db.rollback()
        return None  # Duplicate name


async def get_tags_by_user(db: AsyncSession, user_id: uuid.UUID) -> Sequence[Tag]:
    result = await db.execute(select(Tag).where(Tag.user_id == user_id).order_by(Tag.name))
    return result.scalars().all()


async def get_tag_by_id(db: AsyncSession, tag_id: uuid.UUID) -> Tag | None:
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    return result.scalar_one_or_none()


async def update_tag(db: AsyncSession, tag: Tag, tag_data: TagUpdate) -> Tag | None:
    if tag_data.name is not None:
        tag.name = tag_data.name
    if tag_data.color is not None:
        tag.color = tag_data.color
        
    try:
        await db.commit()
        await db.refresh(tag)
        return tag
    except IntegrityError:
        await db.rollback()
        return None  # Duplicate name


async def delete_tag(db: AsyncSession, tag: Tag) -> None:
    await db.delete(tag)
    await db.commit()