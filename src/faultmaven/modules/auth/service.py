"""
Auth module service layer.

Handles user authentication, registration, and JWT token management.
"""

import uuid
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from jose import jwt, JWTError

from faultmaven.modules.auth.orm import User, RefreshToken
from faultmaven.infrastructure.interfaces import Cache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthService:
    """
    Service for authentication and user management.

    Handles registration, login, token generation and validation.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        cache: Optional[Cache] = None,
        secret_key: str = "dev-secret-change-in-production",
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
        refresh_token_expire_days: int = 7,
    ):
        """
        Initialize auth service.

        Args:
            db_session: Database session
            cache: Optional cache for token blacklist
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token TTL
            refresh_token_expire_days: Refresh token TTL
        """
        self.db = db_session
        self.cache = cache
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self.refresh_token_expire = timedelta(days=refresh_token_expire_days)

    async def register_user(
        self,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
        roles: Optional[list[str]] = None,
    ) -> User:
        """
        Register a new user.

        Args:
            email: User email
            username: Username
            password: Plain text password
            full_name: Optional full name
            roles: Optional list of roles (default: ["user"])

        Returns:
            Created user

        Raises:
            AuthenticationError: If email or username already exists
        """
        # Check if email already exists
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        if result.scalar_one_or_none():
            raise AuthenticationError(f"Email already registered: {email}")

        # Check if username already exists
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        if result.scalar_one_or_none():
            raise AuthenticationError(f"Username already taken: {username}")

        # Hash password
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            roles=roles or ["user"],
            is_active=True,
            is_verified=False,
            user_metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def authenticate_user(
        self, email: str, password: str
    ) -> Tuple[str, str, User]:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            Tuple of (access_token, refresh_token, user)

        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Find user by email
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError("Invalid email or password")

        # Verify password
        if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            raise AuthenticationError("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        # Generate tokens
        access_token = self._create_access_token(user)
        refresh_token_str = await self._create_refresh_token(user)

        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.db.commit()

        return access_token, refresh_token_str, user

    async def validate_token(self, token: str) -> User:
        """
        Validate JWT access token and return user.

        Args:
            token: JWT access token

        Returns:
            User if token is valid

        Raises:
            AuthenticationError: If token is invalid
        """
        # Check blacklist (if cache available)
        if self.cache:
            blacklisted = await self.cache.exists(f"blacklist:{token}")
            if blacklisted:
                raise AuthenticationError("Token has been revoked")

        try:
            # Decode token
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )

            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Invalid token payload")

            # Fetch user
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                raise AuthenticationError("User not found")

            if not user.is_active:
                raise AuthenticationError("User account is inactive")

            return user

        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {e}")

    async def refresh_access_token(
        self, refresh_token: str
    ) -> Tuple[str, str]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: JWT refresh token

        Returns:
            Tuple of (new_access_token, new_refresh_token)

        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token, self.secret_key, algorithms=[self.algorithm]
            )

            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")

            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Invalid token payload")

            # Find refresh token in database
            result = await self.db.execute(
                select(RefreshToken).where(
                    RefreshToken.token == refresh_token,
                    RefreshToken.revoked == False,
                )
            )
            db_token = result.scalar_one_or_none()

            if not db_token:
                raise AuthenticationError("Refresh token not found or revoked")

            if db_token.expires_at < datetime.utcnow():
                raise AuthenticationError("Refresh token expired")

            # Fetch user
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")

            # Revoke old refresh token
            db_token.revoked = True
            db_token.revoked_at = datetime.utcnow()

            # Generate new tokens
            new_access_token = self._create_access_token(user)
            new_refresh_token = await self._create_refresh_token(user)

            await self.db.commit()

            return new_access_token, new_refresh_token

        except JWTError as e:
            raise AuthenticationError(f"Invalid refresh token: {e}")

    async def logout(self, token: str) -> None:
        """
        Logout user by blacklisting their access token.

        Args:
            token: Access token to blacklist
        """
        if self.cache:
            # Add to blacklist with expiration matching token expiration
            await self.cache.set(
                f"blacklist:{token}",
                b"1",
                ttl=self.access_token_expire,
            )

    def _create_access_token(self, user: User) -> str:
        """Create JWT access token."""
        now = datetime.utcnow()
        payload = {
            "sub": user.id,
            "email": user.email,
            "username": user.username,
            "roles": user.roles,
            "type": "access",
            "iat": now,
            "exp": now + self.access_token_expire,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    async def _create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token and store in database."""
        now = datetime.utcnow()
        expires_at = now + self.refresh_token_expire

        payload = {
            "sub": user.id,
            "type": "refresh",
            "iat": now,
            "exp": expires_at,
        }
        token_str = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        # Store in database
        refresh_token = RefreshToken(
            id=str(uuid.uuid4()),
            token=token_str,
            user_id=user.id,
            expires_at=expires_at,
            revoked=False,
            created_at=datetime.utcnow(),
        )
        self.db.add(refresh_token)

        return token_str
