"""
Agent module FastAPI router.

Exposes endpoints for AI agent interactions with RAG and conversation memory.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from faultmaven.modules.agent.service import AgentService
from faultmaven.modules.auth.dependencies import require_auth
from faultmaven.dependencies import get_agent_service


router = APIRouter(prefix="/agent", tags=["agent"])


class ChatRequest(BaseModel):
    """Request to chat with the AI agent."""
    message: str
    stream: bool = False
    use_rag: bool = True


class ChatResponse(BaseModel):
    """Response from the AI agent."""
    response: str


@router.post("/chat/{case_id}", response_model=ChatResponse)
async def chat(
    case_id: str,
    request: ChatRequest,
    user_id: str = Depends(require_auth),
    agent_service: AgentService = Depends(get_agent_service),
):
    """
    Chat with the AI assistant within a case context.

    This endpoint implements the full AI assistant pipeline:
    - Saves user message to case
    - Retrieves relevant context from knowledge base (RAG)
    - Fetches conversation history from case
    - Generates AI response with full context
    - Saves assistant response to case

    Args:
        case_id: Case ID for conversation context
        request: Chat request with message and options
        user_id: Authenticated user ID
        agent_service: Agent service dependency

    Returns:
        AI assistant response (streaming or complete)
    """
    try:
        if request.stream:
            # Return streaming response
            async def generate():
                async for chunk in await agent_service.chat(
                    case_id=case_id,
                    user_id=user_id,
                    message=request.message,
                    stream=True,
                    use_rag=request.use_rag,
                ):
                    yield chunk

            return StreamingResponse(
                generate(),
                media_type="text/plain",
            )
        else:
            # Return complete response
            response = await agent_service.chat(
                case_id=case_id,
                user_id=user_id,
                message=request.message,
                stream=False,
                use_rag=request.use_rag,
            )
            return ChatResponse(response=response)

    except ValueError as e:
        # Case not found or unauthorized
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "agent"}
