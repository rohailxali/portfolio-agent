import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, Conversation, Message
from app.dependencies import get_current_user
from app.agent.orchestrator import run_agent

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    confirm_pending: bool = False
    pending_action: dict | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    tool_calls: list[dict]
    requires_confirmation: bool
    pending_action: dict | None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get or create conversation
    conversation_id = body.conversation_id

    if conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(user_id=current_user.id)
        db.add(conversation)
        await db.flush()
        conversation_id = str(conversation.id)

    # Persist user message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    # Run agent
    confirmed_action = body.pending_action if body.confirm_pending else None
    result = await run_agent(
        user_message=body.message,
        conversation_id=conversation_id,
        user_id=str(current_user.id),
        db=db,
        confirmed_action=confirmed_action,
    )

    # Persist assistant reply
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=result["reply"],
    )
    db.add(assistant_msg)
    await db.flush()

    return ChatResponse(
        reply=result["reply"],
        conversation_id=conversation_id,
        tool_calls=result["tool_calls"],
        requires_confirmation=result["requires_confirmation"],
        pending_action=result["pending_action"],
    )


@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .limit(50)
    )
    convos = result.scalars().all()
    return [{"id": str(c.id), "created_at": c.created_at.isoformat()} for c in convos]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return {
        "id": str(conversation.id),
        "created_at": conversation.created_at.isoformat(),
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in messages
        ],
    }