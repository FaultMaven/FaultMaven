"""
Case factory for creating test cases.
"""

import factory
import uuid
from datetime import datetime

from faultmaven.modules.case.orm import Case, CaseStatus, CasePriority
from tests.factories import AsyncSQLAlchemyFactory
from tests.factories.user import UserFactory


class CaseFactory(AsyncSQLAlchemyFactory):
    """
    Factory for creating test cases.

    Default values:
    - Generated title using Faker
    - Default description
    - Status: CONSULTING (initial state)
    - Priority: MEDIUM
    - No owner (must be provided or use create_with_owner)

    Usage:
        # Create case with specific owner
        user = await UserFactory.create_async(_session=db_session)
        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id
        )

        # Create case with owner in one call (recommended)
        case = await CaseFactory.create_with_owner(_session=db_session)

        # Create case with custom owner
        case = await CaseFactory.create_with_owner(
            _session=db_session,
            owner=existing_user
        )

        # Create high priority case
        case = await CaseFactory.create_with_owner(
            _session=db_session,
            priority=CasePriority.HIGH
        )
    """

    class Meta:
        model = Case

    # Primary key
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))

    # Ownership (MUST be provided or use create_with_owner)
    owner_id = None

    # Basic info
    title = factory.Faker("sentence", nb_words=6)
    description = factory.Faker("paragraph", nb_sentences=3)

    # Status tracking
    status = CaseStatus.CONSULTING
    priority = CasePriority.MEDIUM

    # Investigation data
    context = {}
    case_metadata = {}

    # Tags and categorization
    tags = []
    category = None

    # Timestamps (timezone-naive to match ORM models)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    resolved_at = None
    closed_at = None

    @classmethod
    async def create_with_owner(cls, _session, owner=None, **kwargs):
        """
        Create case with owner (most common use case).

        If owner not provided, creates a new user automatically.

        Args:
            _session: SQLAlchemy AsyncSession
            owner: Optional User instance (creates new if not provided)
            **kwargs: Additional field overrides

        Returns:
            Case instance with owner relationship loaded

        Usage:
            # Create case with new owner
            case = await CaseFactory.create_with_owner(_session=db_session)

            # Create case with existing owner
            case = await CaseFactory.create_with_owner(
                _session=db_session,
                owner=existing_user,
                title="Custom Title"
            )
        """
        if owner is None:
            owner = await UserFactory.create_async(_session=_session)

        kwargs['owner_id'] = owner.id
        case = await cls.create_async(_session=_session, **kwargs)

        # Load the owner relationship
        await _session.refresh(case, attribute_names=['owner'])

        return case
