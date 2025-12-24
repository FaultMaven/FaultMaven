"""
User factory for creating test users.
"""

import factory
import uuid
from datetime import datetime

from faultmaven.modules.auth.orm import User
from tests.factories import AsyncSQLAlchemyFactory


class UserFactory(AsyncSQLAlchemyFactory):
    """
    Factory for creating test users.

    Default values:
    - Sequential email: user0@example.com, user1@example.com, ...
    - Sequential username: user0, user1, ...
    - Password hash for "password"
    - Active and verified user
    - Default "user" role

    Usage:
        # Create user with defaults
        user = await UserFactory.create_async(_session=db_session)

        # Create user with custom email
        user = await UserFactory.create_async(
            _session=db_session,
            email="custom@example.com"
        )

        # Create admin user
        admin = await UserFactory.create_async(
            _session=db_session,
            roles=["user", "admin"]
        )

        # Create inactive user
        inactive = await UserFactory.create_async(
            _session=db_session,
            is_active=False
        )
    """

    class Meta:
        model = User

    # Primary key
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))

    # Basic info
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")

    # Password hash for "password" (bcrypt)
    # Generated with: bcrypt.hashpw(b"password", bcrypt.gensalt())
    password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqNhxQqD0K"

    # Profile
    full_name = factory.Faker("name")
    avatar_url = None

    # Authorization
    roles = ["user"]
    is_active = True
    is_verified = True

    # Metadata
    user_metadata = {}

    # Timestamps (timezone-naive to match ORM models)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    last_login_at = None
