"""
Test data factories using factory_boy.

Provides factories for creating test data with sensible defaults.
Build on-demand - only create factories as tests need them.
"""

import factory


class AsyncSQLAlchemyFactory(factory.Factory):
    """
    Base factory for async SQLAlchemy models.

    Provides async methods for creating instances and adding to database.
    """

    class Meta:
        abstract = True

    @classmethod
    async def create_async(cls, _session, **kwargs):
        """
        Create instance and add to database session.

        Args:
            _session: SQLAlchemy AsyncSession
            **kwargs: Field overrides

        Returns:
            Created model instance (flushed and refreshed)

        Usage:
            user = await UserFactory.create_async(
                _session=db_session,
                email="custom@example.com"
            )
        """
        instance = cls.build(**kwargs)
        _session.add(instance)
        await _session.flush()
        await _session.refresh(instance)
        return instance

    @classmethod
    async def create_batch_async(cls, size, _session, **kwargs):
        """
        Create multiple instances in batch.

        Args:
            size: Number of instances to create
            _session: SQLAlchemy AsyncSession
            **kwargs: Field overrides (applied to all instances)

        Returns:
            List of created model instances

        Usage:
            users = await UserFactory.create_batch_async(
                size=10,
                _session=db_session
            )
        """
        instances = [cls.build(**kwargs) for _ in range(size)]
        _session.add_all(instances)
        await _session.flush()

        for instance in instances:
            await _session.refresh(instance)

        return instances
