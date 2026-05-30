"""AI 写作 API：支持多模型供应商配置。"""

from __future__ import annotations

import json
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..config import settings, ModelConfig, ModelProvider
from ..models.project import Project
from ..models.chapter import Chapter
from ..services.ai_service import AIService

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ── 模型配置 API ──

class ProviderCreate(BaseModel):
    id: str
    name: str
    base_url: str = ""
    api_key: str = ""
    provider_type: str = "openai"
    models: list[str] = []


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    provider_type: Optional[str] = None
    models: Optional[list[str]] = None
    enabled: Optional[bool] = None


class ActiveModelUpdate(BaseModel):
    provider_id: str
    model: str


class ProviderResponse(BaseModel):
    id: str
    name: str
    base_url: str
    provider_type: str
    models: list[str]
    enabled: bool
    has_key: bool  # 不暴露实际 key


@router.get("/providers")
async def list_providers():
    """获取所有模型供应商。"""
    config = settings.model_config_obj
    return [
        ProviderResponse(
            id=p.id,
            name=p.name,
            base_url=p.base_url,
            provider_type=p.provider_type,
            models=p.models,
            enabled=p.enabled,
            has_key=bool(p.api_key),
        )
        for p in config.providers
    ]


@router.post("/providers")
async def create_provider(data: ProviderCreate):
    """添加模型供应商。"""
    config = settings.model_config_obj
    # 检查 ID 重复
    if any(p.id == data.id for p in config.providers):
        raise HTTPException(status_code=400, detail=f"供应商 ID '{data.id}' 已存在")

    provider = ModelProvider(**data.model_dump())
    config.providers.append(provider)
    # 如果是第一个供应商，自动设为激活
    if not config.active_provider_id:
        config.active_provider_id = provider.id
        if provider.models:
            config.active_model = provider.models[0]
    settings.save_model_config(config)
    return {"message": "供应商已添加", "id": provider.id}


@router.put("/providers/{provider_id}")
async def update_provider(provider_id: str, data: ProviderUpdate):
    """更新模型供应商。api_key 留空或不传则保持原值。"""
    config = settings.model_config_obj
    provider = next((p for p in config.providers if p.id == provider_id), None)
    if not provider:
        raise HTTPException(status_code=404, detail="供应商不存在")

    update_data = data.model_dump(exclude_unset=True)
    # api_key 留空 = 不修改，需要过滤掉
    if "api_key" in update_data and not update_data["api_key"]:
        del update_data["api_key"]
    for key, value in update_data.items():
        setattr(provider, key, value)
    settings.save_model_config(config)
    return {"message": "供应商已更新"}


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str):
    """删除模型供应商。"""
    config = settings.model_config_obj
    config.providers = [p for p in config.providers if p.id != provider_id]
    if config.active_provider_id == provider_id:
        config.active_provider_id = config.providers[0].id if config.providers else ""
        config.active_model = config.providers[0].models[0] if config.providers and config.providers[0].models else ""
    settings.save_model_config(config)
    return {"message": "供应商已删除"}


@router.post("/active-model")
async def set_active_model(data: ActiveModelUpdate):
    """设置当前使用的模型。"""
    config = settings.model_config_obj
    provider = next((p for p in config.providers if p.id == data.provider_id), None)
    if not provider:
        raise HTTPException(status_code=404, detail="供应商不存在")
    if data.model not in provider.models:
        raise HTTPException(status_code=400, detail="模型不在供应商的模型列表中")

    config.active_provider_id = data.provider_id
    config.active_model = data.model
    settings.save_model_config(config)
    return {"message": "模型已切换", "provider": data.provider_id, "model": data.model}


@router.get("/active-model")
async def get_active_model():
    """获取当前激活的模型。"""
    config = settings.model_config_obj
    provider = next((p for p in config.providers if p.id == config.active_provider_id), None)
    return {
        "provider_id": config.active_provider_id,
        "provider_name": provider.name if provider else "",
        "model": config.active_model,
        "configured": bool(provider and provider.api_key),
    }


@router.post("/test-connection")
async def test_connection(provider_id: str):
    """测试供应商连接。"""
    config = settings.model_config_obj
    provider = next((p for p in config.providers if p.id == provider_id), None)
    if not provider:
        raise HTTPException(status_code=404, detail="供应商不存在")

    try:
        db_gen = get_db()
        db = await db_gen.__anext__()
        ai = AIService(db)
        # 临时覆盖配置进行测试
        ai._provider = provider
        ai._config = ModelConfig(
            providers=[provider],
            active_provider_id=provider.id,
            active_model=provider.models[0] if provider.models else "",
        )
        result = await ai._call_ai("你是一个助手", "请回复连接成功", max_tokens=20)
        return {"success": True, "message": f"连接成功：{result[:50]}"}
    except Exception as e:
        return {"success": False, "message": f"连接失败：{str(e)}"}


# ── AI 写作 API（保持原有接口） ──

class OutlineGenerationRequest(BaseModel):
    project_id: int
    answers: dict


@router.post("/generate-outline")
async def generate_outline(data: OutlineGenerationRequest, db: AsyncSession = Depends(get_db)):
    """根据 5 问立项生成大纲。"""
    ai = AIService(db)
    if not ai.is_configured:
        raise HTTPException(status_code=400, detail="未配置模型供应商，请在设置中添加")

    result = await db.execute(select(Project).where(Project.id == data.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    outline = await ai.generate_outline(data.project_id, data.answers)

    from ..models.document import Document
    doc_result = await db.execute(
        select(Document).where(Document.project_id == data.project_id, Document.doc_type == "outline")
    )
    doc = doc_result.scalar_one_or_none()
    if doc:
        doc.content = outline
    else:
        doc = Document(project_id=data.project_id, doc_type="outline", title="大纲", content=outline)
        db.add(doc)

    project.synopsis = data.answers.get("synopsis", "")
    project.core_conflict = data.answers.get("core_conflict", "")
    project.genre = data.answers.get("genre", "")
    await db.commit()

    return {"outline": outline, "project_id": data.project_id}


@router.post("/analyze/{chapter_id}")
async def analyze_chapter(chapter_id: int, db: AsyncSession = Depends(get_db)):
    """写前分析。"""
    ai = AIService(db)
    if not ai.is_configured:
        raise HTTPException(status_code=400, detail="未配置模型供应商")

    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    analysis = await ai.analyze_for_chapter(chapter.project_id, chapter)
    chapter.pre_analysis = analysis
    await db.commit()
    return analysis


@router.post("/plan-scenes/{chapter_id}")
async def plan_scenes(chapter_id: int, db: AsyncSession = Depends(get_db)):
    """场景规划。"""
    ai = AIService(db)
    if not ai.is_configured:
        raise HTTPException(status_code=400, detail="未配置模型供应商")

    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    pre_analysis = chapter.pre_analysis
    if not pre_analysis:
        pre_analysis = await ai.analyze_for_chapter(chapter.project_id, chapter)
        chapter.pre_analysis = pre_analysis

    scenes = await ai.plan_scenes(chapter.project_id, chapter, pre_analysis)
    chapter.scene_plan = {"scenes": scenes}
    await db.commit()
    return {"scenes": scenes}


@router.post("/write-stream/{chapter_id}")
async def write_chapter_stream(
    chapter_id: int,
    scene_plan: Optional[list[dict]] = None,
    db: AsyncSession = Depends(get_db),
):
    """流式生成正文。"""
    ai = AIService(db)
    if not ai.is_configured:
        raise HTTPException(status_code=400, detail="未配置模型供应商")

    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    if not scene_plan:
        if not chapter.pre_analysis:
            chapter.pre_analysis = await ai.analyze_for_chapter(chapter.project_id, chapter)
        scenes = await ai.plan_scenes(chapter.project_id, chapter, chapter.pre_analysis)
        scene_plan = scenes
        chapter.scene_plan = {"scenes": scene_plan}
        await db.commit()

    async def event_generator():
        full_content = []
        async for chunk in ai.write_chapter_stream(chapter.project_id, chapter, scene_plan):
            full_content.append(chunk)
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

        final_content = "".join(full_content)
        chapter.content = final_content
        chapter.word_count = len(final_content.replace(" ", "").replace("\n", ""))
        chapter.status = "completed"

        project_result = await db.execute(select(Project).where(Project.id == chapter.project_id))
        project = project_result.scalar_one_or_none()
        if project:
            project.current_chapter_count = max(project.current_chapter_count, chapter.chapter_number)
        await db.commit()

        yield f"data: {json.dumps({'done': True, 'word_count': chapter.word_count}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/polish")
async def polish_text(text: str, instruction: str = "润色以下段落", db: AsyncSession = Depends(get_db)):
    ai = AIService(db)
    if not ai.is_configured:
        raise HTTPException(status_code=400, detail="未配置模型供应商")
    result = await ai.polish_text(text, instruction)
    return {"result": result}


@router.post("/rewrite")
async def rewrite_text(text: str, instruction: str = "重写以下段落", db: AsyncSession = Depends(get_db)):
    ai = AIService(db)
    if not ai.is_configured:
        raise HTTPException(status_code=400, detail="未配置模型供应商")
    result = await ai.rewrite_text(text, instruction)
    return {"result": result}


@router.post("/expand")
async def expand_text(text: str, instruction: str = "扩写以下段落", db: AsyncSession = Depends(get_db)):
    ai = AIService(db)
    if not ai.is_configured:
        raise HTTPException(status_code=400, detail="未配置模型供应商")
    result = await ai.expand_text(text, instruction)
    return {"result": result}


# ── 对话接口 ──

class ChatRequest(BaseModel):
    project_id: int
    message: str
    history: Optional[list[dict]] = None
    system_override: Optional[str] = None  # 自定义 system prompt


async def _build_full_project_context(project_id: int, db) -> str:
    """加载完整项目上下文：大纲、世界观、法则、角色、伏笔、时间线。"""
    from ..models.chapter import Chapter
    from ..models.character import Character
    from ..models.foreshadowing import Foreshadowing
    from ..models.timeline import TimelineEvent
    from ..models.document import Document
    from ..models.project import Project
    from sqlalchemy import select

    sections = []

    # 项目信息
    proj = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if proj:
        sections.append(f"## 项目信息\n- 书名：{proj.name}\n- 题材：{proj.genre}\n- 进度：{proj.current_chapter_count}/{proj.target_chapters} 章\n- 核心冲突：{proj.core_conflict}\n- 主线梗概：{proj.synopsis}")

    # L3 宪法记忆：世界观、法则、冲突设计、设定记录
    doc_types = ["outline", "worldview", "rules", "conflict", "settings", "dialogue"]
    doc_labels = {"outline": "大纲", "worldview": "世界观", "rules": "法则", "conflict": "冲突设计", "settings": "设定记录", "dialogue": "角色台词库"}
    for dt in doc_types:
        doc = (await db.execute(select(Document).where(Document.project_id == project_id, Document.doc_type == dt))).scalar_one_or_none()
        if doc and doc.content and len(doc.content.strip()) > 20:
            max_len = 5000 if dt == "outline" else 3000
            sections.append(f"## {doc_labels.get(dt, dt)}\n{doc.content[:max_len]}")

    # 角色（完整详情）
    chars = (await db.execute(select(Character).where(Character.project_id == project_id))).scalars().all()
    if chars:
        char_docs = []
        for c in chars:
            role_label = {"protagonist": "主角", "antagonist": "反派", "supporting": "配角"}.get(c.role, c.role)
            profile = c.profile_data or {}
            # 优先使用完整文档，否则用结构化字段
            if profile.get("full_document"):
                char_docs.append(f"### {c.name}（{role_label}）\n{profile['full_document'][:2000]}")
            else:
                details = []
                for key in ["性格核心", "核心价值观", "致命缺陷", "内心渴望", "背景故事", "成长目标"]:
                    if profile.get(key):
                        details.append(f"- {key}：{profile[key]}")
                char_docs.append(f"### {c.name}（{role_label}）\n" + "\n".join(details) if details else f"### {c.name}（{role_label}）")
        sections.append("## 角色详情\n" + "\n\n".join(char_docs))

    # 伏笔（完整详情）
    fss = (await db.execute(select(Foreshadowing).where(Foreshadowing.project_id == project_id))).scalars().all()
    if fss:
        fs_docs = []
        for f in fss:
            fs_docs.append(f"### {f.name}（{f.status}，第{f.chapter_planted}章埋设" + (f"→第{f.chapter_resolved}章回收" if f.chapter_resolved else "") + "）\n{f.notes[:1000] if f.notes else '暂无详细设计'}")
        sections.append("## 伏笔详情\n" + "\n\n".join(fs_docs))

    # 时间线（完整详情）
    tl = (await db.execute(select(TimelineEvent).where(TimelineEvent.project_id == project_id).order_by(TimelineEvent.chapter_number))).scalars().all()
    if tl:
        tl_lines = [f"- 第{e.chapter_number}章 [{e.event_type}]：{e.description}" for e in tl]
        sections.append("## 时间线\n" + "\n".join(tl_lines))

    # 章节列表
    chapters = (await db.execute(select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.chapter_number))).scalars().all()
    if chapters:
        ch_lines = [f"- 第{ch.chapter_number}章 {ch.title or ''}（{ch.word_count}字，{ch.status}）" for ch in chapters]
        sections.append("## 章节列表\n" + "\n".join(ch_lines))

    return "\n\n".join(sections)


@router.post("/chat")
async def chat_stream(data: ChatRequest, db: AsyncSession = Depends(get_db)):
    """通用对话接口，AI 拥有完整项目上下文并可自主执行操作。"""
    ai = AIService(db)
    if not ai.is_configured:
        raise HTTPException(status_code=400, detail="未配置模型供应商")

    # 优先使用自定义 system prompt
    if data.system_override:
        system_prompt = data.system_override
    else:
        # 加载完整项目上下文
        project_context = await _build_full_project_context(data.project_id, db)

        # 根据用户消息动态加载相关 references
        from ..core.prompt_manager import load_reference
        ref_context = ""
        msg_lower = data.message.lower()
        # 根据关键词加载对应的 reference
        ref_map = {
            "角色": ["character-building", "character-template"],
            "冲突": ["conflict-design"],
            "世界观": ["worldbuilding-logic", "worldbuilding-presentation"],
            "伏笔": ["suspense-design"],
            "对话": ["dialogue-writing"],
            "钩子": ["hook-techniques"],
            "情绪": ["reader-compensation"],
            "群像": ["ensemble-writing"],
            "非线性": ["nonlinear-narrative"],
            "金手指": ["golden-finger-design"],
            "大纲": ["outline-template", "plot-structures"],
            "节奏": ["chapter-guide"],
        }
        loaded_refs = set()
        for keyword, refs in ref_map.items():
            if keyword in msg_lower:
                for ref in refs:
                    if ref not in loaded_refs:
                        content = load_reference(ref)
                        if not content.startswith("[Reference not found"):
                            ref_context += f"\n\n---\n\n{content[:2000]}"
                            loaded_refs.add(ref)

        # 始终加载核心创作规则
        for ref in ["chapter-guide", "dialogue-writing", "hook-techniques"]:
            if ref not in loaded_refs:
                content = load_reference(ref)
                if not content.startswith("[Reference not found"):
                    ref_context += f"\n\n---\n\n{content[:2000]}"
                    loaded_refs.add(ref)

        system_prompt = f"""你是用户的AI创作助手，拥有对这个小说项目的完整读写能力。你可以查看、创建、修改项目中的所有内容。

## 项目完整数据
{project_context}

## 你的能力
你可以像IDE助手一样操作这个项目：

### 读取
- 你可以看到项目的大纲全文、所有角色详情、伏笔、时间线、章节
- 当用户问到相关内容时，直接引用项目数据回答

### 创建
当用户要求创建内容时，直接创建并确认：
- 创建角色（单个或多个/群像）
- 创建伏笔
- 创建时间线事件
- 更新已有内容

### 操作指令格式
在回复末尾输出操作指令（可多个）：
[ACTION:CREATE_CHARACTER:{{"name":"名字","role":"protagonist/antagonist/supporting","profile_data":{{"性格核心":"...","核心价值观":"...","致命缺陷":"...","内心渴望":"...","背景故事":"...","成长目标":"...","完整描述":"完整markdown"}}}}]
[ACTION:CREATE_FORESHADOWING:{{"name":"名称","foreshadow_type":"类型","chapter_planted":0,"notes":"完整markdown"}}]
[ACTION:CREATE_TIMELINE:{{"chapter_number":0,"event_time":"时间","description":"描述","event_type":"plot/relationship/character_change"}}]
[ACTION:CREATE_CHAPTER:{{"title":"章节标题","content":"完整正文内容markdown"}}]
[ACTION:UPDATE_CHARACTER:ID:{{字段更新}}]
[ACTION:UPDATE_FORESHADOWING:ID:{{字段更新}}]
[ACTION:UPDATE_CHAPTER:ID:{{"content":"更新后的正文"}}]

## 重要：你必须输出操作指令
当用户要求你做任何创建/修改操作时，你**必须**在回复末尾输出 [ACTION:...] 指令。这是系统保存你工作的唯一方式。
- 如果用户让你写章节，必须输出 [ACTION:CREATE_CHAPTER:...]
- 如果你只给回复文本但不输出 ACTION，你的工作成果将不会被保存
- 操作指令格式是机器可读的，必须严格遵守

## 工作原则
1. 用户说什么，你就做什么——不要问太多确认问题，直接行动
2. 写章节时，先输出正文，最后一行输出 [ACTION:CREATE_CHAPTER:{{"title":"章节标题"}}]
3. 创建角色时给出完整、详细的设计
4. 创建群像时，每个角色一个独立ACTION
5. 主动引用项目中已有的内容
6. 操作指令放最后一行

## 回复风格
- 中文，像一个真正的创作伙伴
- 直接行动，不问"你确定吗？"
- 创建完成后告诉用户做了什么"""
        # 注入参考知识
        if ref_context:
            system_prompt += f"\n\n## 创作参考知识（来自专业写作指南）\n{ref_context[:8000]}"
        system_prompt += f"\n\n## 项目记忆\n{(await ai.memory.build_memory_for_writing(data.project_id, 0))[:1000]}"

    async def event_generator():
        # 检查是否是"确认写作"（用户确认了写前分析后触发）
        is_confirm_write = '确认写作' in data.message or '开始写' in data.message or '就这样写' in data.message

        if is_confirm_write:
            # 用户确认了，直接生成正文
            # 找到最近创建的章节
            chapters_result = await db.execute(
                select(Chapter).where(Chapter.project_id == data.project_id, Chapter.status == "writing")
                .order_by(Chapter.chapter_number.desc())
            )
            chapter = chapters_result.scalar_one_or_none()
            if chapter:
                # 从对话历史中提取写前分析
                analysis_text = ""
                for h in reversed(data.history or []):
                    if h.get("role") == "assistant" and "写前分析" in h.get("content", ""):
                        analysis_text = h["content"]
                        break

                write_prompt = f"""请根据以下写前分析，撰写第 {chapter.chapter_number} 章。

## 写前分析
{analysis_text[:3000]}

## 输出格式（必须严格遵守）
第一行输出标题，用 # 开头：
# 章节标题

然后空一行，直接开始正文。不要输出其他任何元信息。

## 写作要求
1. 默认目标 3000-5000 字，不够就扩写细节
2. 开头前 20% 必须有钩子
3. 每章至少推进一条线、回应一个旧悬念、留下一个新钩子
4. 场景内部的 Beats 只作隐性骨架，正文要写成连续叙事
5. **必须严格遵守项目记忆中的世界观设定和法则，不能自相矛盾**
6. **角色行为必须符合其性格设定，不能 OOC**
7. **展示不讲述**：用动作、对话、环境细节承载情绪，不要空泛描述
8. **长短句交替**，用动作、反应、对话承载情绪
9. **不要写 AI 味**：避免"此外""然而""值得注意"等套语
10. **伏笔追踪**：项目记忆中有活跃伏笔，本章应至少推进或呼应一条
11. **情绪补偿**：主角受挫后必须有补偿，不能长期纯受气

请直接输出："""

                full_content = ""
                async for chunk in ai._call_ai_stream(system_prompt, write_prompt, max_tokens=8192, history=data.history):
                    full_content += chunk
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

                # 保存正文到章节
                clean_content = re.sub(r'\[ACTION:\w+:.+?\]', '', full_content).strip()
                # 提取标题（第一行 # 开头）
                title_match = re.match(r'^#\s*(.+)', clean_content)
                if title_match:
                    chapter.title = title_match.group(1).strip()
                    # 从正文中移除标题行
                    clean_content = re.sub(r'^#\s*.+\n?', '', clean_content).strip()
                chapter.content = clean_content
                chapter.word_count = len(clean_content.replace(" ", "").replace("\n", ""))
                chapter.status = "completed"
                await db.commit()

                # 伏笔追踪：检测正文是否涉及活跃伏笔
                from ..models.foreshadowing import Foreshadowing
                fss = (await db.execute(select(Foreshadowing).where(Foreshadowing.project_id == data.project_id, Foreshadowing.status == "active"))).scalars().all()
                mentioned_fs = []
                for fs in fss:
                    if fs.name in clean_content:
                        mentioned_fs.append(fs.name)
                if mentioned_fs:
                    fs_msg = f"\n\n📌 **伏笔追踪**：本章涉及伏笔 → {', '.join(mentioned_fs)}"
                else:
                    fs_msg = ""

                save_msg = f"\n\n---\n✅ 已保存「第{chapter.chapter_number}章 {chapter.title}」（{chapter.word_count}字）{fs_msg}"
                yield f"data: {json.dumps({'content': save_msg}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'content': '没有找到待写作的章节，请先说「写下一章」。'}, ensure_ascii=False)}\n\n"

        else:
            # 正常对话流程
            action_results = await _handle_user_intent(data, db)

            # 如果创建了章节，先做写前分析再让 AI 输出
            chapter_created = None
            for ar in action_results:
                if ar.startswith("[ACTION:CHAPTER_CREATED:"):
                    parts = ar.split(":")
                    ch_id = int(parts[2])
                    chapter_created = (await db.execute(select(Chapter).where(Chapter.id == ch_id))).scalar_one_or_none()

            if chapter_created:
                # 写前分析模式：让 AI 先输出分析+场景规划，而不是直接写正文
                context_prefix = f"""[系统通知] 已创建第{chapter_created.chapter_number}章「{chapter_created.title}」。

请执行写前分析。**要求：每项只写一句话，不要展开论述。**

### 写前分析
- 视角：本章跟谁的视角（一句话）
- 目标：本章要推进什么（一句话）
- 冲突：核心冲突是什么（一句话）
- 钩子方向：结尾怎么勾住读者（一句话）
- 主角状态：主角当前处境（一句话）

### 场景规划（3-5个场景）
每个场景只写：
**场景N：[名称]**
- 地点：xxx
- 人物：xxx
- 事件：xxx
- 类型：铺垫/冲突/高潮/转折/收尾
- 情绪：xxx→xxx

分析完成后，用户会确认再写正文。用户确认后会说「确认写作」。

"""
                full_prompt = context_prefix + data.message
            else:
                context_prefix = ""
                if action_results:
                    context_prefix = f"\n\n[系统通知] 你刚才为用户执行了以下操作：\n{chr(10).join(action_results)}\n请基于这些操作结果回复用户。\n\n"
                full_prompt = context_prefix + data.message

            full_content = ""
            async for chunk in ai._call_ai_stream(system_prompt, full_prompt, max_tokens=8192, history=data.history):
                full_content += chunk
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            # 如果创建了章节但还没写正文，把分析结果保存到 pre_analysis
            if chapter_created and not chapter_created.content:
                chapter_created.pre_analysis = {"analysis": full_content[:2000]}
                await db.commit()

            # 操作结果
            if action_results:
                result_text = "\n\n---\n" + "\n".join(action_results)
                yield f"data: {json.dumps({'content': result_text}, ensure_ascii=False)}\n\n"

        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _handle_user_intent(data: ChatRequest, db) -> list[str]:
    """分析用户意图，主动执行操作，不依赖 AI 输出格式。"""
    from ..models.chapter import Chapter
    from ..models.character import Character
    from ..models.project import Project
    from sqlalchemy import select, func as sqlfunc
    import re

    msg = data.message.lower()
    results = []

    # ── 写章节 ──
    if any(k in msg for k in ['写第', '写下一章', '生成正文', '写正文', '创作第', '续写', '写个章节', '输出章节']):
        # 找到下一个章节号
        count_result = await db.execute(select(sqlfunc.count(Chapter.id)).where(Chapter.project_id == data.project_id))
        max_num = count_result.scalar() or 0

        # 从消息中提取章节标题
        title_match = re.search(r'第(\d+)章\s*(.*)', data.message)
        if title_match:
            ch_num = int(title_match.group(1))
            ch_title = title_match.group(2).strip()
        else:
            ch_num = max_num + 1
            ch_title = f"第{ch_num}章"

        # 先创建空章节
        chapter = Chapter(
            project_id=data.project_id,
            chapter_number=ch_num,
            title=ch_title,
            status="writing",
        )
        db.add(chapter)

        # 更新项目章节数
        proj = (await db.execute(select(Project).where(Project.id == data.project_id))).scalar_one_or_none()
        if proj:
            proj.current_chapter_count = (proj.current_chapter_count or 0) + 1

        await db.commit()
        await db.refresh(chapter)
        results.append(f"[ACTION:CHAPTER_CREATED:{chapter.id}:{ch_num}:{ch_title}]")
        return results

    # ── 创建角色 ──
    if any(k in msg for k in ['创建角色', '新建角色', '添加角色', '设计角色', '建立角色', '帮我设计一个']):
        if any(k in msg for k in ['角色', '人物', '反派', '主角', '配角']):
            # 提取角色名
            name_match = re.search(r'(?:角色|人物|设计一个?|创建)\s*[""「]?(.+?)[""」]?\s*(?:，|,|。|的|是)', msg)
            char_name = name_match.group(1) if name_match else "新角色"
            char = Character(
                project_id=data.project_id,
                name=char_name,
                role="supporting",
                profile_data={"created_from_chat": True, "user_message": data.message},
            )
            db.add(char)
            await db.commit()
            await db.refresh(char)
            results.append(f"[ACTION:CHARACTER_CREATED:{char.id}:{char_name}]")
            return results

    # ── 创建伏笔 ──
    if any(k in msg for k in ['创建伏笔', '埋伏笔', '添加伏笔', '设计伏笔']):
        from ..models.foreshadowing import Foreshadowing
        fs_match = re.search(r'(?:伏笔|设计)\s*[""「]?(.+?)[""」]?', msg)
        fs_name = fs_match.group(1) if fs_match else "新伏笔"
        fs = Foreshadowing(
            project_id=data.project_id,
            name=fs_name,
            notes=data.message,
        )
        db.add(fs)
        await db.commit()
        await db.refresh(fs)
        results.append(f"[ACTION:FORESHADOWING_CREATED:{fs.id}:{fs_name}]")
        return results

    # ── 创建时间线事件 ──
    if any(k in msg for k in ['创建事件', '记录事件', '添加事件']):
        from ..models.timeline import TimelineEvent
        ch_match = re.search(r'第(\d+)章', data.message)
        event = TimelineEvent(
            project_id=data.project_id,
            chapter_number=int(ch_match.group(1)) if ch_match else 0,
            description=data.message[:200],
            event_type="plot",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        results.append(f"[ACTION:TIMELINE_CREATED:{event.id}]")
        return results

    return results
