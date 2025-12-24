"""
Integration tests for AuthService.

Tests the actual AuthService business logic without hitting HTTP endpoints.
Verifies password hashing, authentication, and user management.
"""

import pytest
import bcrypt
from faultmaven.modules.auth.service import AuthService, AuthenticationError
from faultmaven.modules.auth.orm import User
from sqlalchemy import select


@pytest.mark.asyncio
@pytest.mark.integration
async def test_register_user_hashing(db_session):
    """Verify that registering a user correctly hashes their password."""
    # Create service with test session and secret key
    service = AuthService(
        db_session=db_session,
        cache=None,  # No Redis cache needed for this test
        secret_key="test-secret-key"
    )

    # Register user
    user = await service.register_user(
        email="security_test@fm.com",
        username="sec_user",
        password="MySecretPassword123!",
        full_name="Security Tester"
    )

    # Verify user was created
    assert user.id is not None
    assert user.email == "security_test@fm.com"
    assert user.username == "sec_user"
    assert user.full_name == "Security Tester"

    # Verify password was hashed (not stored as plaintext)
    assert user.password_hash != "MySecretPassword123!"
    assert user.password_hash.startswith("$2b$")  # bcrypt hash format

    # Verify password can be verified with bcrypt
    assert bcrypt.checkpw(
        "MySecretPassword123!".encode(),
        user.password_hash.encode()
    )

    print("✅ Password hashing works correctly")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_register_user_duplicate_email(db_session):
    """Verify that duplicate email registration is rejected."""
    service = AuthService(
        db_session=db_session,
        cache=None,
        secret_key="test-secret-key"
    )

    # Register first user
    await service.register_user(
        email="duplicate@fm.com",
        username="user1",
        password="Password123!"
    )

    # Try to register with same email
    with pytest.raises(AuthenticationError, match="Email already registered"):
        await service.register_user(
            email="duplicate@fm.com",  # Same email
            username="user2",  # Different username
            password="Password123!"
        )

    print("✅ Duplicate email protection works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_register_user_duplicate_username(db_session):
    """Verify that duplicate username registration is rejected."""
    service = AuthService(
        db_session=db_session,
        cache=None,
        secret_key="test-secret-key"
    )

    # Register first user
    await service.register_user(
        email="user1@fm.com",
        username="duplicate_user",
        password="Password123!"
    )

    # Try to register with same username
    with pytest.raises(AuthenticationError, match="Username already taken"):
        await service.register_user(
            email="user2@fm.com",  # Different email
            username="duplicate_user",  # Same username
            password="Password123!"
        )

    print("✅ Duplicate username protection works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_authenticate_user_success(db_session):
    """Verify login logic works with correct credentials."""
    service = AuthService(
        db_session=db_session,
        cache=None,
        secret_key="test-secret-key"
    )

    # 1. Register user
    await service.register_user(
        email="login_test@fm.com",
        username="login_user",
        password="LoginPass123!",
        full_name="Login Tester"
    )

    # 2. Authenticate with email and password
    access_token, refresh_token, user = await service.authenticate_user(
        email="login_test@fm.com",
        password="LoginPass123!"
    )

    # Verify tokens were generated
    assert access_token is not None
    assert isinstance(access_token, str)
    assert len(access_token) > 0

    assert refresh_token is not None
    assert isinstance(refresh_token, str)
    assert len(refresh_token) > 0

    # Verify user was returned
    assert user is not None
    assert user.username == "login_user"
    assert user.email == "login_test@fm.com"
    assert user.is_active is True

    print("✅ Authentication with correct credentials works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_authenticate_user_wrong_password(db_session):
    """Verify login fails with wrong password."""
    service = AuthService(
        db_session=db_session,
        cache=None,
        secret_key="test-secret-key"
    )

    # Register user
    await service.register_user(
        email="fail_test@fm.com",
        username="fail_user",
        password="RealPassword123!",
        full_name="Fail Tester"
    )

    # Try to authenticate with wrong password
    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        await service.authenticate_user(
            email="fail_test@fm.com",
            password="WrongPassword"
        )

    print("✅ Wrong password is rejected")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_authenticate_user_nonexistent_email(db_session):
    """Verify login fails with non-existent email."""
    service = AuthService(
        db_session=db_session,
        cache=None,
        secret_key="test-secret-key"
    )

    # Try to authenticate non-existent user
    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        await service.authenticate_user(
            email="ghost@fm.com",
            password="whatever"
        )

    print("✅ Non-existent email is rejected")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_validate_token_success(db_session):
    """Verify token validation works for valid tokens."""
    service = AuthService(
        db_session=db_session,
        cache=None,
        secret_key="test-secret-key"
    )

    # Register and authenticate user
    user = await service.register_user(
        email="token_test@fm.com",
        username="token_user",
        password="TokenPass123!"
    )

    access_token, _, _ = await service.authenticate_user(
        email="token_test@fm.com",
        password="TokenPass123!"
    )

    # Validate the token
    validated_user = await service.validate_token(access_token)

    assert validated_user is not None
    assert validated_user.id == user.id
    assert validated_user.email == user.email

    print("✅ Token validation works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_validate_token_invalid(db_session):
    """Verify token validation fails for invalid tokens."""
    service = AuthService(
        db_session=db_session,
        cache=None,
        secret_key="test-secret-key"
    )

    # Try to validate an invalid token
    with pytest.raises(AuthenticationError, match="Invalid token"):
        await service.validate_token("invalid.token.here")

    print("✅ Invalid token is rejected")
