"""项目导出 API：导出章节为 TXT 文件。"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.chapter import Chapter
from ..models.project import Project

router = APIRouter(prefix="/api/projects/{project_id}/export", tags=["export"])


@router.get("/txt")
async def export_all_chapters(project_id: int, db: AsyncSession = Depends(get_db)):
    """导出所有已完成章节为 TXT 文件。"""
    proj = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")

    chapters = (await db.execute(
        select(Chapter)
        .where(Chapter.project_id == project_id, Chapter.status == "completed")
        .order_by(Chapter.chapter_number)
    )).scalars().all()

    if not chapters:
        raise HTTPException(status_code=404, detail="没有已完成的章节")

    # 组装 TXT 内容
    lines = [f"《{proj.name}》", ""]
    for ch in chapters:
        title = ch.title or f"第{ch.chapter_number}章"
        lines.append(f"第{ch.chapter_number}章 {title}")
        lines.append("")
        lines.append(ch.content or "")
        lines.append("")
        lines.append("=" * 40)
        lines.append("")

    content = "\n".join(lines)
    filename = f"{proj.name}.txt"

    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/txt/{chapter_id}")
async def export_single_chapter(project_id: int, chapter_id: int, db: AsyncSession = Depends(get_db)):
    """导出单个章节为 TXT 文件。"""
    proj = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")

    chapter = (await db.execute(
        select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id)
    )).scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    if not chapter.content:
        raise HTTPException(status_code=400, detail="章节还没有内容")

    title = chapter.title or f"第{chapter.chapter_number}章"
    content = f"《{proj.name}》\n\n第{chapter.chapter_number}章 {title}\n\n{chapter.content}"
    filename = f"第{chapter.chapter_number}章 {title}.txt"

    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
