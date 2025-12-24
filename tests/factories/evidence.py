"""
Evidence factory for creating test evidence.
"""

import factory
import uuid
from datetime import datetime

from faultmaven.modules.evidence.orm import Evidence, EvidenceType
from tests.factories import AsyncSQLAlchemyFactory
from tests.factories.user import UserFactory
from tests.factories.case import CaseFactory


class EvidenceFactory(AsyncSQLAlchemyFactory):
    """
    Factory for creating test evidence.

    Default values:
    - Sequential filename: log_0.txt, log_1.txt, ...
    - Default evidence type: LOG
    - Mock content hash
    - Auto-generated storage path

    Usage:
        # Create evidence for a specific case
        case = await CaseFactory.create_with_owner(_session=db_session)
        evidence = await EvidenceFactory.create_async(
            _session=db_session,
            case=case,
            uploaded_by_user=case.owner
        )

        # Create evidence with custom type
        evidence = await EvidenceFactory.create_async(
            _session=db_session,
            case=case,
            uploaded_by_user=user,
            evidence_type=EvidenceType.SCREENSHOT,
            filename="error_screen.png"
        )
    """

    class Meta:
        model = Evidence

    # Primary key
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))

    # File metadata
    filename = factory.Sequence(lambda n: f"log_{n}.txt")
    original_filename = factory.SelfAttribute("filename")
    file_type = "text/plain"
    file_size = 1024

    # Storage reference (auto-generated based on case_id)
    storage_path = factory.LazyAttribute(
        lambda o: f"evidence/{o.case_id}/{o.filename}"
    )

    # Evidence categorization
    evidence_type = EvidenceType.LOG
    description = "Test Log File"
    tags = []
    evidence_metadata = {}

    # Timestamps (timezone-naive to match ORM models)
    uploaded_at = factory.LazyFunction(datetime.utcnow)

    # Relationships - case_id and uploaded_by must be provided
    # Don't use SubFactory to avoid circular dependencies and null constraint issues
    case_id = None  # Must be provided
    uploaded_by = None  # Must be provided

    @classmethod
    async def create_for_case(cls, _session, case, user=None, **kwargs):
        """
        Create evidence for a specific case (most common use case).

        Args:
            _session: SQLAlchemy AsyncSession
            case: Case instance
            user: Optional User instance (defaults to case owner)
            **kwargs: Additional field overrides

        Returns:
            Evidence instance

        Usage:
            case = await CaseFactory.create_with_owner(_session=db_session)
            evidence = await EvidenceFactory.create_for_case(
                _session=db_session,
                case=case,
                filename="critical_error.log"
            )
        """
        if user is None:
            # Use case owner by default
            user = case.owner

        kwargs["case_id"] = case.id
        kwargs["uploaded_by"] = user.id

        return await cls.create_async(_session=_session, **kwargs)
