"""章节质量检查 API：集成现有 Python 脚本。"""

from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.chapter import Chapter

router = APIRouter(prefix="/api/projects/{project_id}/quality", tags=["quality"])

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "skills" / "novel-create" / "scripts"
CHAPTERS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "skills" / "novel-create" / "manuscript"


def _run_script(script_name: str, args: list[str]) -> dict:
    """运行 Python 脚本并返回结果。"""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        return {"error": f"脚本不存在: {script_name}"}

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(SCRIPTS_DIR),
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else "",
        }
    except subprocess.TimeoutExpired:
        return {"error": "脚本执行超时"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/{chapter_id}")
async def check_chapter_quality(project_id: int, chapter_id: int, db: AsyncSession = Depends(get_db)):
    """对指定章节执行全部质量检查。"""
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    if not chapter.content:
        return {"error": "章节还没有内容"}

    # 写入临时文件供脚本读取
    tmp_dir = CHAPTERS_DIR
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = tmp_dir / f"{chapter.chapter_number:03d}_check.md"
    tmp_file.write_text(chapter.content, encoding="utf-8")

    checks = {}

    # 1. 字数检查
    wc_result = _run_script("check_chapter_wordcount.py", [str(tmp_file)])
    checks["wordcount"] = {
        "output": wc_result.get("output", ""),
        "success": wc_result.get("success", False),
    }

    # 2. 情绪曲线检查
    ec_result = _run_script("check_emotion_curve.py", [str(tmp_file)])
    checks["emotion_curve"] = {
        "output": ec_result.get("output", ""),
        "success": ec_result.get("success", False),
    }

    # 3. 爽点/毒点检测
    thrill_result = _run_script("extract_thrills.py", [str(tmp_file)])
    checks["thrills"] = {
        "output": thrill_result.get("output", ""),
        "success": thrill_result.get("success", False),
    }

    # 清理临时文件
    try:
        tmp_file.unlink()
    except:
        pass

    return checks


@router.get("/{chapter_id}/summary")
async def get_quality_summary(project_id: int, chapter_id: int, db: AsyncSession = Depends(get_db)):
    """获取章节质量摘要（用于聊天中展示）。"""
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    if not chapter.content:
        return {"summary": "章节还没有内容，无法检查。"}

    content = chapter.content
    word_count = len(content.replace(" ", "").replace("\n", ""))

    # 基础统计
    paragraphs = [p for p in content.split("\n") if p.strip()]
    avg_para_len = sum(len(p) for p in paragraphs) / max(len(paragraphs), 1)

    # 简单的 AI 痕迹检测
    ai_words = ["此外", "然而", "强调", "值得注意的是", "不可否认", "综上所述", "总而言之"]
    ai_count = sum(content.count(w) for w in ai_words)

    # 生成摘要
    lines = [
        f"📊 **第{chapter.chapter_number}章质量报告**",
        f"",
        f"**基础数据：**",
        f"- 字数：{word_count} {'✅' if 3000 <= word_count <= 5000 else '⚠️'}（目标 3000-5000）",
        f"- 段落数：{len(paragraphs)}",
        f"- 平均段落长度：{int(avg_para_len)} 字",
        f"",
        f"**AI 痕迹检测：**",
        f"- 高风险套语：{ai_count} 处 {'✅' if ai_count < 3 else '⚠️ 偏多'}",
    ]

    if word_count < 3000:
        lines.append(f"\n⚠️ **字数不足**：当前 {word_count} 字，建议扩展到 3000+ 字")
    elif word_count > 5000:
        lines.append(f"\n⚠️ **字数偏多**：当前 {word_count} 字，考虑是否需要精简")

    if ai_count >= 3:
        lines.append(f"⚠️ **AI 痕迹明显**：建议替换高频套语为具体描写")

    # 段落节奏检查
    if avg_para_len > 200:
        lines.append(f"⚠️ **段落偏长**：平均 {int(avg_para_len)} 字/段，考虑拆分")
    elif avg_para_len < 30:
        lines.append(f"⚠️ **段落偏短**：平均 {int(avg_para_len)} 字/段，考虑合并")

    # 情绪补偿检查：检测主角是否受挫后有补偿
    setback_words = ["失败", "受伤", "失去", "被杀", "背叛", "受辱", "被擒", "亏损", "惨败", "牺牲", "死亡", "死亡", "崩溃", "绝望", "痛苦"]
    compensation_words = ["反制", "反击", "获胜", "逃脱", "获得", "领悟", "突破", "觉醒", "成长", "收获", "逆转", "翻盘", "胜利", "成功", "救出", "获救", "突破", "领悟"]
    setback_count = sum(content.count(w) for w in setback_words)
    compensation_count = sum(content.count(w) for w in compensation_words)
    lines.append(f"")
    lines.append(f"**情绪补偿检查：**")
    lines.append(f"- 受挫信号：{setback_count} 处")
    lines.append(f"- 补偿信号：{compensation_count} 处")
    if setback_count > 0 and compensation_count == 0:
        lines.append(f"⚠️ **缺少情绪补偿**：本章有受挫但没有补偿，读者可能感到压抑")
    elif setback_count > 0 and compensation_count > 0:
        lines.append(f"✅ 受挫与补偿平衡")
    else:
        lines.append(f"✅ 无明显受挫/补偿需求")

    summary = "\n".join(lines)
    return {"summary": summary, "word_count": word_count, "ai_count": ai_count}
