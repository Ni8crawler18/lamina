"""Natural-language agent endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.ai.agent import ChatAgent

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None


@router.post("")
async def chat(body: ChatRequest, session: AsyncSession = Depends(get_session)):
    return await ChatAgent(session).process(body.message, body.history)
