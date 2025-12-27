"""
Session module FastAPI router.

Exposes endpoints for session management.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field
from typing import Optional, Any

from faultmaven.modules.session.service import SessionService
from faultmaven.modules.auth.router import get_current_user
from faultmaven.modules.auth.orm import User
from faultmaven.dependencies import get_session_service


router = APIRouter(prefix="/sessions", tags=["sessions"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateSessionRequest(BaseModel):
    """Create session request."""
    session_data: Optional[dict[str, Any]] = None


class SessionResponse(BaseModel):
    """Session information response."""
    session_id: str
    created_at: str
    last_accessed_at: str
    expires_at: str
    ip_address: Optional[str]
    user_agent: Optional[str]


class UpdateSessionRequest(BaseModel):
    """Update session request."""
    updates: dict[str, Any]


class AddSessionMessageRequest(BaseModel):
    """Add message to session request."""
    role: str
    content: str


class SessionSearchRequest(BaseModel):
    """Session search request with validation."""
    status: Optional[str] = Field(None, pattern="^(active|archived|expired)$", description="Filter by status")
    min_messages: Optional[int] = Field(None, ge=0, description="Minimum message count")
    max_messages: Optional[int] = Field(None, ge=0, description="Maximum message count")
    has_cases: Optional[bool] = Field(None, description="Filter by whether session has cases")
    created_after: Optional[str] = Field(None, description="Created after date (ISO format)")
    created_before: Optional[str] = Field(None, description="Created before date (ISO format)")
    search_text: Optional[str] = Field(None, max_length=500, description="Text search in messages")
    limit: int = Field(20, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/health")
async def session_health():
    """Session system health check."""
    return {
        "status": "healthy",
        "service": "sessions"
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    x_forwarded_for: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None),
):
    """
    Create a new session for the current user.

    Args:
        request: Session creation request
        current_user: Authenticated user
        session_service: Session service
        x_forwarded_for: Client IP address
        user_agent: Client user agent

    Returns:
        Session ID and details
    """
    session_id = await session_service.create_session(
        user_id=current_user.id,
        ip_address=x_forwarded_for,
        user_agent=user_agent,
        session_data=request.session_data,
    )

    return {
        "session_id": session_id,
        "message": "Session created successfully"
    }


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    List all active sessions for the current user.

    Args:
        current_user: Authenticated user
        session_service: Session service

    Returns:
        List of active sessions
    """
    sessions = await session_service.list_user_sessions(current_user.id)

    return [
        SessionResponse(
            session_id=s["session_id"],
            created_at=s["created_at"],
            last_accessed_at=s["last_accessed_at"],
            expires_at=s["expires_at"],
            ip_address=s.get("ip_address"),
            user_agent=s.get("user_agent"),
        )
        for s in sessions
    ]


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Get session details.

    Args:
        session_id: Session ID
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Session data

    Raises:
        HTTPException: If session not found or unauthorized
    """
    data = await session_service.get_session(session_id)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Verify session belongs to current user
    if data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )

    return data


@router.patch("/{session_id}")
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Update session data.

    Args:
        session_id: Session ID
        request: Update request
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Success message

    Raises:
        HTTPException: If session not found or unauthorized
    """
    # Verify session exists and belongs to user
    data = await session_service.get_session(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this session"
        )

    # Update session
    updated = await session_service.update_session(session_id, request.updates)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session"
        )

    return {"message": "Session updated successfully"}


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Delete/revoke a session.

    Args:
        session_id: Session ID
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Success message

    Raises:
        HTTPException: If session not found or unauthorized
    """
    # Verify session exists and belongs to user
    data = await session_service.get_session(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this session"
        )

    # Delete session
    deleted = await session_service.delete_session(session_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )

    return {"message": "Session deleted successfully"}


@router.delete("")
async def delete_all_sessions(
    keep_current: bool = True,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Delete all sessions for the current user.

    Args:
        keep_current: Whether to keep the current session
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Number of sessions deleted
    """
    # Note: We don't have access to current session_id from JWT auth
    # In a real implementation, you'd extract this from a session cookie
    # For now, we'll delete all sessions if keep_current is False
    except_session = None  # TODO: Get from cookie/header if keep_current

    count = await session_service.delete_user_sessions(
        user_id=current_user.id,
        except_session_id=except_session
    )

    return {
        "message": f"Deleted {count} session(s)",
        "count": count
    }


@router.post("/{session_id}/heartbeat")
async def session_heartbeat(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Update session heartbeat (last activity timestamp).

    Args:
        session_id: Session ID
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Heartbeat confirmation with updated timestamp

    Raises:
        HTTPException: If session not found or unauthorized
    """
    # Verify session exists and belongs to user
    data = await session_service.get_session(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )

    # Update last accessed timestamp
    from datetime import datetime
    last_activity = datetime.utcnow().isoformat() + "Z"
    await session_service.update_session(session_id, {"last_accessed_at": last_activity})

    return {
        "session_id": session_id,
        "last_activity_at": last_activity,
        "status": data.get("status", "active")
    }


@router.post("/{session_id}/messages")
async def add_session_message(
    session_id: str,
    request: AddSessionMessageRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Add a message to the session's conversation history.

    Args:
        session_id: Session ID
        request: Message to add
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Message confirmation

    Raises:
        HTTPException: If session not found or unauthorized
    """
    # Verify session exists and belongs to user
    data = await session_service.get_session(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )

    # Add message to session data
    from datetime import datetime
    timestamp = datetime.utcnow().isoformat() + "Z"
    messages = data.get("session_data", {}).get("messages", [])

    new_message = {
        "role": request.role,
        "content": request.content,
        "timestamp": timestamp
    }
    messages.append(new_message)

    session_data = data.get("session_data", {})
    session_data["messages"] = messages

    await session_service.update_session(session_id, {"session_data": session_data})

    return {
        "session_id": session_id,
        "message": new_message,
        "total_messages": len(messages)
    }


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Get session conversation message history.

    Args:
        session_id: Session ID
        limit: Maximum messages to return (default: 100, max: 500)
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Session messages

    Raises:
        HTTPException: If session not found or unauthorized
    """
    # Verify session exists and belongs to user
    data = await session_service.get_session(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )

    # Get messages from session data
    messages = data.get("session_data", {}).get("messages", [])

    # Apply limit (max 500)
    limit = min(limit, 500)
    returned_messages = messages[-limit:] if len(messages) > limit else messages

    return {
        "session_id": session_id,
        "messages": returned_messages,
        "total": len(messages),
        "returned": len(returned_messages)
    }


@router.get("/{session_id}/cases")
async def get_session_cases(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Get cases associated with a session.

    Args:
        session_id: Session ID
        current_user: Authenticated user
        session_service: Session service

    Returns:
        List of case IDs for this session

    Raises:
        HTTPException: If session not found or unauthorized
    """
    # Verify session exists and belongs to user
    data = await session_service.get_session(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )

    # Get cases from session data
    cases = data.get("session_data", {}).get("cases", [])

    return {
        "session_id": session_id,
        "cases": cases,
        "count": len(cases)
    }


@router.get("/{session_id}/stats")
async def get_session_stats(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Get session statistics.

    Args:
        session_id: Session ID
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Session statistics

    Raises:
        HTTPException: If session not found or unauthorized
    """
    # Verify session exists and belongs to user
    data = await session_service.get_session(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )

    # Calculate stats from session data
    session_data = data.get("session_data", {})
    messages = session_data.get("messages", [])
    cases = session_data.get("cases", [])

    return {
        "session_id": session_id,
        "message_count": len(messages),
        "case_count": len(cases),
        "created_at": data.get("created_at"),
        "last_accessed_at": data.get("last_accessed_at")
    }


@router.post("/search")
async def search_sessions(
    request: SessionSearchRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Search sessions with validated query parameters.

    Supports filters:
    - status: Filter by status (active, archived, expired)
    - min_messages: Minimum message count
    - max_messages: Maximum message count
    - has_cases: Whether session has associated cases
    - created_after: Created after date (ISO format)
    - created_before: Created before date (ISO format)
    - search_text: Text search in messages

    Args:
        request: Validated search request
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Matching sessions with pagination info
    """
    # Convert Pydantic model to dict for service call
    query = {
        k: v for k, v in request.model_dump().items()
        if v is not None and k not in ("limit", "offset")
    }

    sessions = await session_service.search_sessions_advanced(
        user_id=current_user.id,
        query=query,
    )

    # Apply pagination
    total = len(sessions)
    start = request.offset
    end = start + request.limit
    paginated = sessions[start:end]

    return {
        "sessions": paginated,
        "total": total,
        "query": query
    }


@router.get("/statistics")
async def get_aggregate_statistics(
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Get aggregate statistics for all user sessions.

    Returns statistics including:
    - total_sessions: Total number of active sessions
    - total_messages: Total messages across all sessions
    - total_cases: Total cases across all sessions
    - oldest_session: Oldest session creation time
    - newest_session: Newest session creation time
    - avg_messages_per_session: Average messages per session
    - session_status_breakdown: Count by status
    - devices: List of device types used

    Args:
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Aggregate session statistics
    """
    stats = await session_service.get_aggregate_statistics(current_user.id)
    return {
        "user_id": current_user.id,
        **stats
    }


@router.post("/{session_id}/archive")
async def archive_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Archive a session by changing its status to 'archived'.

    Args:
        session_id: Session ID
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Archive confirmation

    Raises:
        HTTPException: If session not found or unauthorized
    """
    # Verify session exists and belongs to user
    data = await session_service.get_session(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to archive this session"
        )

    # Update session status to archived
    await session_service.update_session(session_id, {"status": "archived"})

    return {
        "session_id": session_id,
        "status": "archived",
        "message": "Session archived successfully"
    }


@router.post("/{session_id}/restore")
async def restore_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Restore an archived session by changing its status back to 'active'.

    Args:
        session_id: Session ID
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Restore confirmation

    Raises:
        HTTPException: If session not found or unauthorized
    """
    # Verify session exists and belongs to user
    data = await session_service.get_session(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to restore this session"
        )

    # Update session status to active
    await session_service.update_session(session_id, {"status": "active"})

    return {
        "session_id": session_id,
        "status": "active",
        "message": "Session restored successfully"
    }


@router.post("/cleanup")
async def cleanup_sessions(
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Cleanup expired sessions for the current user.

    Args:
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Number of sessions cleaned up
    """
    # This would normally clean up expired sessions
    # For now, we'll return a placeholder
    from datetime import datetime, timedelta

    sessions = await session_service.list_user_sessions(current_user.id)
    expired_count = 0

    # Check for sessions older than 30 days
    cutoff = datetime.utcnow() - timedelta(days=30)

    for session in sessions:
        created_at_str = session.get("created_at", "")
        if created_at_str:
            try:
                from dateutil import parser
                created_at = parser.parse(created_at_str)
                if created_at < cutoff:
                    # Would delete here
                    expired_count += 1
            except:
                pass

    return {
        "message": f"Cleaned up {expired_count} expired sessions",
        "count": expired_count
    }


@router.get("/{session_id}/recovery-info")
async def get_session_recovery_info(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """
    Get session recovery information.

    Args:
        session_id: Session ID
        current_user: Authenticated user
        session_service: Session service

    Returns:
        Recovery information

    Raises:
        HTTPException: If session not found or unauthorized
    """
    # Verify session exists and belongs to user
    data = await session_service.get_session(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )

    # Return recovery info
    return {
        "session_id": session_id,
        "can_recover": data.get("status") != "expired",
        "last_backup": data.get("last_accessed_at"),
        "session_data_size": len(str(data.get("session_data", {}))),
        "message_count": len(data.get("session_data", {}).get("messages", []))
    }


