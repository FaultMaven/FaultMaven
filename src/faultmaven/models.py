"""
Central ORM model imports.

Import all ORM models here to ensure they're registered with SQLAlchemy
before the application starts.
"""

# Import all ORM models to register them with SQLAlchemy
from faultmaven.modules.auth.orm import User, RefreshToken
from faultmaven.modules.session.orm import SessionAudit
from faultmaven.modules.case.orm import Case, Hypothesis, Solution, CaseMessage
from faultmaven.modules.evidence.orm import Evidence
from faultmaven.modules.knowledge.orm import Document, SearchQuery
from faultmaven.modules.agent.orm import ChatSession, LLMRequest

__all__ = [
    "User",
    "RefreshToken",
    "SessionAudit",
    "Case",
    "Hypothesis",
    "Solution",
    "CaseMessage",
    "Evidence",
    "Document",
    "SearchQuery",
    "ChatSession",
    "LLMRequest",
]
