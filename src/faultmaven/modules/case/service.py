"""
Case module service layer.

Handles case lifecycle management including hypotheses and solutions.
"""

import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from faultmaven.modules.case.orm import Case, Hypothesis, Solution, CaseMessage, CaseStatus, CasePriority


class CaseService:
    """
    Service for case management.

    Manages cases with ownership verification and sub-resource handling.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize case service.

        Args:
            db_session: Database session
        """
        self.db = db_session

    async def create_case(
        self,
        owner_id: str,
        title: str,
        description: str,
        priority: CasePriority = CasePriority.MEDIUM,
        context: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
        category: Optional[str] = None,
    ) -> Case:
        """
        Create a new case.

        Args:
            owner_id: User ID who owns the case
            title: Case title
            description: Case description
            priority: Case priority level
            context: Additional context data
            tags: Case tags
            category: Case category

        Returns:
            Created case with initial CONSULTING status
        """
        # Create case with initial CONSULTING status
        case = Case(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            title=title,
            description=description,
            status=CaseStatus.CONSULTING,  # Initial status
            priority=priority,
            context=context or {},
            case_metadata={},
            tags=tags or [],
            category=category,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(case)
        await self.db.commit()
        await self.db.refresh(case)

        return case

    async def get_case(self, case_id: str, user_id: Optional[str] = None) -> Optional[Case]:
        """
        Get a case by ID with optional ownership verification.

        Args:
            case_id: Case ID
            user_id: Optional user ID for ownership verification

        Returns:
            Case if found and authorized, None otherwise
        """
        result = await self.db.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()

        if not case:
            return None

        # Verify ownership if user_id provided
        if user_id and case.owner_id != user_id:
            return None

        return case

    async def list_cases(
        self,
        owner_id: str,
        status: Optional[CaseStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Case], int]:
        """
        List cases for a user.

        Args:
            owner_id: User ID to filter by
            status: Optional status filter
            limit: Maximum number of cases to return
            offset: Offset for pagination

        Returns:
            Tuple of (cases, total_count)
        """
        # Build count query with same filters
        count_query = select(func.count()).select_from(Case).where(Case.owner_id == owner_id)

        if status:
            count_query = count_query.where(Case.status == status)

        # Get total count (optimized - no row fetching)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Build data query with same filters
        query = select(Case).where(Case.owner_id == owner_id)

        if status:
            query = query.where(Case.status == status)

        query = query.order_by(Case.updated_at.desc()).limit(limit).offset(offset)

        # Get paginated results
        result = await self.db.execute(query)
        cases = result.scalars().all()

        return list(cases), total

    async def update_case(
        self,
        case_id: str,
        user_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[CaseStatus] = None,
        priority: Optional[CasePriority] = None,
        tags: Optional[list[str]] = None,
        category: Optional[str] = None,
    ) -> Optional[Case]:
        """
        Update a case.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            title: Optional new title
            description: Optional new description
            status: Optional new status
            priority: Optional new priority
            tags: Optional new tags
            category: Optional new category

        Returns:
            Updated case or None if not found/unauthorized
        """
        # Get case with ownership check
        case = await self.get_case(case_id, user_id)
        if not case:
            return None

        # Apply updates
        if title is not None:
            case.title = title
        if description is not None:
            case.description = description
        if status is not None:
            case.status = status
            # Set resolved_at/closed_at based on status
            if status == CaseStatus.RESOLVED and not case.resolved_at:
                case.resolved_at = datetime.utcnow()
            if status == CaseStatus.CLOSED and not case.closed_at:
                case.closed_at = datetime.utcnow()
        if priority is not None:
            case.priority = priority
        if tags is not None:
            case.tags = tags
        if category is not None:
            case.category = category

        case.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(case)

        return case

    async def delete_case(self, case_id: str, user_id: str) -> bool:
        """
        Delete a case.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification

        Returns:
            True if deleted, False if not found/unauthorized
        """
        # Check ownership first
        case = await self.get_case(case_id, user_id)
        if not case:
            return False

        # Delete case (cascade will delete hypotheses, solutions, messages, evidence)
        await self.db.delete(case)
        await self.db.commit()

        return True

    async def add_hypothesis(
        self,
        case_id: str,
        user_id: str,
        title: str,
        description: str,
        confidence: Optional[float] = None,
    ) -> Optional[Hypothesis]:
        """
        Add a hypothesis to a case.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            title: Hypothesis title
            description: Hypothesis description
            confidence: Optional confidence level (0.0 to 1.0)

        Returns:
            Created hypothesis or None if case not found/unauthorized
        """
        # Get case with ownership check
        case = await self.get_case(case_id, user_id)
        if not case:
            return None

        # Create hypothesis - add directly to session (avoid lazy loading)
        hypothesis = Hypothesis(
            id=str(uuid.uuid4()),
            case_id=case_id,
            title=title,
            description=description,
            confidence=confidence,
            validated=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Add to session directly (avoids async lazy loading issues)
        self.db.add(hypothesis)

        await self.db.commit()
        await self.db.refresh(hypothesis)

        return hypothesis

    async def add_solution(
        self,
        case_id: str,
        user_id: str,
        title: str,
        description: str,
        implementation_steps: Optional[list[str]] = None,
    ) -> Optional[Solution]:
        """
        Add a solution to a case.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            title: Solution title
            description: Solution description
            implementation_steps: Optional list of implementation steps

        Returns:
            Created solution or None if case not found/unauthorized
        """
        # Get case with ownership check
        case = await self.get_case(case_id, user_id)
        if not case:
            return None

        # Create solution - add directly to session (avoid lazy loading)
        solution = Solution(
            id=str(uuid.uuid4()),
            case_id=case_id,
            title=title,
            description=description,
            implementation_steps=implementation_steps or [],
            implemented=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Add to session directly (avoids async lazy loading issues)
        self.db.add(solution)

        await self.db.commit()
        await self.db.refresh(solution)

        return solution

    async def add_message(
        self,
        case_id: str,
        user_id: str,
        role: str,
        content: str,
        message_metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[CaseMessage]:
        """
        Add a message to a case.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            role: Message role (user, assistant, system)
            content: Message content
            message_metadata: Optional message metadata

        Returns:
            Created message or None if case not found/unauthorized
        """
        # Get case with ownership check
        case = await self.get_case(case_id, user_id)
        if not case:
            return None

        # Create message - add directly to session (avoid lazy loading)
        message = CaseMessage(
            id=str(uuid.uuid4()),
            case_id=case_id,
            role=role,
            content=content,
            message_metadata=message_metadata or {},
            created_at=datetime.utcnow(),
        )

        # Add to session directly (avoids async lazy loading issues)
        self.db.add(message)

        await self.db.commit()
        await self.db.refresh(message)

        return message

    async def list_case_messages(
        self,
        case_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Optional[list[CaseMessage]]:
        """
        List messages for a case.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            limit: Maximum number of messages
            offset: Pagination offset

        Returns:
            List of messages or None if case not found/unauthorized
        """
        # Get case with ownership check
        case = await self.get_case(case_id, user_id)
        if not case:
            return None

        # Query messages with pagination
        query = (
            select(CaseMessage)
            .where(CaseMessage.case_id == case_id)
            .order_by(CaseMessage.created_at.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        messages = result.scalars().all()

        return list(messages)
