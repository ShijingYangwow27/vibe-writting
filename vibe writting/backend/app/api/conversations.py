"""对话历史管理 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.conversation import Conversation, ChatMessage

router = APIRouter(prefix="/api/projects/{project_id}/conversations", tags=["conversations"])


class MessageCreate(BaseModel):
    role: str
    content: str
    message_type: str = "text"
    metadata_json: Optional[dict] = None


# ── 对话管理 ──

@router.get("")
async def list_conversations(project_id: int, db: AsyncSession = Depends(get_db)):
    """获取项目的所有对话。"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.updated_at.desc())
    )
    convs = list(result.scalars().all())
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat()}
        for c in convs
    ]


@router.post("")
async def create_conversation(project_id: int, db: AsyncSession = Depends(get_db)):
    """创建新对话。"""
    conv = Conversation(project_id=project_id, title="新对话")
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return {"id": conv.id, "title": conv.title}


@router.delete("/{conv_id}")
async def delete_conversation(project_id: int, conv_id: int, db: AsyncSession = Depends(get_db)):
    """删除对话。"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.project_id == project_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    await db.delete(conv)
    await db.commit()
    return {"message": "对话已删除"}


# ── 消息管理 ──

@router.get("/{conv_id}/messages")
async def list_messages(project_id: int, conv_id: int, db: AsyncSession = Depends(get_db)):
    """获取对话的所有消息。"""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conv_id)
        .order_by(ChatMessage.created_at)
    )
    msgs = list(result.scalars().all())
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "message_type": m.message_type,
            "metadata_json": m.metadata_json,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]


@router.post("/{conv_id}/messages")
async def add_message(project_id: int, conv_id: int, data: MessageCreate, db: AsyncSession = Depends(get_db)):
    """添加消息到对话。"""
    # 验证对话存在
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.project_id == project_id)
    )
    conv = conv_result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    msg = ChatMessage(
        conversation_id=conv_id,
        role=data.role,
        content=data.content,
        message_type=data.message_type,
        metadata_json=data.metadata_json,
    )
    db.add(msg)

    # 更新对话标题（用第一条用户消息的前20个字）
    if data.role == "user" and conv.title == "新对话":
        conv.title = data.content[:20] + ("..." if len(data.content) > 20 else "")

    await db.commit()
    await db.refresh(msg)
    return {"id": msg.id, "role": msg.role, "content": msg.content}


@router.get("/{conv_id}/history")
async def get_conversation_history(project_id: int, conv_id: int, limit: int = 30, db: AsyncSession = Depends(get_db)):
    """获取对话历史（用于 AI 调用）。"""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conv_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    msgs = list(reversed(result.scalars().all()))
    return [
        {"role": m.role, "content": m.content[:5000]}
        for m in msgs
    ]


class RewindRequest(BaseModel):
    message_id: int  # 回退到这条消息（保留这条，删除之后的）


@router.post("/{conv_id}/rewind")
async def rewind_conversation(project_id: int, conv_id: int, data: RewindRequest, db: AsyncSession = Depends(get_db)):
    """回退对话到指定消息（删除该消息之后的所有消息）。"""
    # 验证对话存在
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.project_id == project_id)
    )
    conv = conv_result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 找到目标消息
    target_result = await db.execute(
        select(ChatMessage).where(
            ChatMessage.id == data.message_id,
            ChatMessage.conversation_id == conv_id,
        )
    )
    target_msg = target_result.scalar_one_or_none()
    if not target_msg:
        raise HTTPException(status_code=404, detail="消息不存在")

    # 删除目标消息之后的所有消息
    later_msgs = await db.execute(
        select(ChatMessage).where(
            ChatMessage.conversation_id == conv_id,
            ChatMessage.created_at > target_msg.created_at,
        )
    )
    for msg in later_msgs.scalars().all():
        await db.delete(msg)

    await db.commit()
    return {"message": "已回退", "kept_up_to": data.message_id}
