"""伏笔、时间线、角色管理 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.foreshadowing import Foreshadowing
from ..models.timeline import TimelineEvent
from ..models.character import Character

router = APIRouter(prefix="/api/projects/{project_id}", tags=["story-elements"])


# ── 伏笔 CRUD ──

class ForeshadowingCreate(BaseModel):
    name: str
    foreshadow_type: str = ""
    chapter_planted: int = 0
    notes: str = ""


class ForeshadowingUpdate(BaseModel):
    name: Optional[str] = None
    foreshadow_type: Optional[str] = None
    chapter_planted: Optional[int] = None
    chapter_resolved: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None


@router.get("/foreshadowings")
async def list_foreshadowings(project_id: int, status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(Foreshadowing).where(Foreshadowing.project_id == project_id)
    if status:
        query = query.where(Foreshadowing.status == status)
    result = await db.execute(query.order_by(Foreshadowing.chapter_planted))
    return list(result.scalars().all())


@router.post("/foreshadowings")
async def create_foreshadowing(project_id: int, data: ForeshadowingCreate, db: AsyncSession = Depends(get_db)):
    fs = Foreshadowing(project_id=project_id, **data.model_dump())
    db.add(fs)
    await db.commit()
    await db.refresh(fs)
    return fs


@router.put("/foreshadowings/{fs_id}")
async def update_foreshadowing(project_id: int, fs_id: int, data: ForeshadowingUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Foreshadowing).where(Foreshadowing.id == fs_id, Foreshadowing.project_id == project_id)
    )
    fs = result.scalar_one_or_none()
    if not fs:
        raise HTTPException(status_code=404, detail="伏笔不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(fs, key, value)
    await db.commit()
    await db.refresh(fs)
    return fs


@router.delete("/foreshadowings/{fs_id}")
async def delete_foreshadowing(project_id: int, fs_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Foreshadowing).where(Foreshadowing.id == fs_id, Foreshadowing.project_id == project_id)
    )
    fs = result.scalar_one_or_none()
    if not fs:
        raise HTTPException(status_code=404, detail="伏笔不存在")
    await db.delete(fs)
    await db.commit()
    return {"message": "伏笔已删除"}


# ── 时间线 CRUD ──

class TimelineCreate(BaseModel):
    chapter_number: int = 0
    event_time: str = ""
    description: str = ""
    event_type: str = "plot"


class TimelineUpdate(BaseModel):
    chapter_number: Optional[int] = None
    event_time: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None


@router.get("/timeline")
async def list_timeline(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TimelineEvent)
        .where(TimelineEvent.project_id == project_id)
        .order_by(TimelineEvent.chapter_number)
    )
    return list(result.scalars().all())


@router.post("/timeline")
async def create_timeline_event(project_id: int, data: TimelineCreate, db: AsyncSession = Depends(get_db)):
    event = TimelineEvent(project_id=project_id, **data.model_dump())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.put("/timeline/{event_id}")
async def update_timeline_event(project_id: int, event_id: int, data: TimelineUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TimelineEvent).where(TimelineEvent.id == event_id, TimelineEvent.project_id == project_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(event, key, value)
    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/timeline/{event_id}")
async def delete_timeline_event(project_id: int, event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TimelineEvent).where(TimelineEvent.id == event_id, TimelineEvent.project_id == project_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    await db.delete(event)
    await db.commit()
    return {"message": "事件已删除"}


# ── 角色 CRUD ──

class CharacterCreate(BaseModel):
    name: str
    role: str = "supporting"
    profile_data: Optional[dict] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    profile_data: Optional[dict] = None


@router.get("/characters")
async def list_characters(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Character).where(Character.project_id == project_id)
    )
    return list(result.scalars().all())


@router.post("/characters")
async def create_character(project_id: int, data: CharacterCreate, db: AsyncSession = Depends(get_db)):
    char = Character(project_id=project_id, **data.model_dump())
    db.add(char)
    await db.commit()
    await db.refresh(char)
    return char


@router.put("/characters/{char_id}")
async def update_character(project_id: int, char_id: int, data: CharacterUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Character).where(Character.id == char_id, Character.project_id == project_id)
    )
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(char, key, value)
    await db.commit()
    await db.refresh(char)
    return char


@router.delete("/characters/{char_id}")
async def delete_character(project_id: int, char_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Character).where(Character.id == char_id, Character.project_id == project_id)
    )
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")
    await db.delete(char)
    await db.commit()
    return {"message": "角色已删除"}
