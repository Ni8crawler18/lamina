"""Chat agent route."""

from fastapi import APIRouter

router = APIRouter(tags=["chat"])


@router.post("/api/chat")
async def chat(message: dict):
    from server.agents.chat import process_message
    return await process_message(message.get("message", ""))
