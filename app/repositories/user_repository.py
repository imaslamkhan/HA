from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken, User, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_visitor(
        self, *, full_name: str, email: str, phone: str, password_hash: str
    ) -> User:
        user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            password_hash=password_hash,
            role=UserRole.VISITOR,
            # Keep visitor accounts inactive until OTP verification activates them.
            is_active=False,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_email_or_phone(self, identifier: str) -> User | None:
        result = await self.session.execute(
            select(User).where(or_(User.email == identifier, User.phone == identifier))
        )
        return result.scalar_one_or_none()

    async def create_refresh_token(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        device_name: str | None = None,
        ip_address: str | None = None,
    ) -> RefreshToken:
        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_name=device_name,
            ip_address=ip_address,
        )
        self.session.add(refresh_token)
        await self.session.flush()
        return refresh_token

    async def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token_hash: str, revoked_at: datetime) -> RefreshToken | None:
        refresh_token = await self.get_refresh_token(token_hash)
        if refresh_token is not None:
            refresh_token.revoked_at = revoked_at
            await self.session.flush()
        return refresh_token
    
    async def get_by_id(self, user_id: str) -> User | None:
        """Get user by ID"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_refresh_tokens(self, user_id: str) -> list[RefreshToken]:
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(UTC),
            ).order_by(RefreshToken.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def revoke_refresh_token_by_id(self, token_id: str, revoked_at: datetime) -> bool:
        """
        Revoke refresh token by its ID.
        
        Returns True if revoked, False if not found.
        """
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.id == token_id)
        )
        token = result.scalar_one_or_none()
        if token:
            token.revoked_at = revoked_at
            await self.session.flush()
            return True
        return False
    
    async def revoke_all_refresh_tokens(
        self, 
        *, 
        user_id: str, 
        exclude_token_hash: str | None = None,
        revoked_at: datetime
    ) -> int:
        """
        Revoke all refresh tokens for a user.
        
        Optionally exclude one token (for keeping current session when changing password).
        
        Returns count of revoked tokens.
        """
        query = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC)
        )
        
        if exclude_token_hash:
            query = query.where(RefreshToken.token_hash != exclude_token_hash)
        
        result = await self.session.execute(query)
        tokens = list(result.scalars().all())
        
        count = 0
        for token in tokens:
            token.revoked_at = revoked_at
            count += 1
        
        await self.session.flush()
        return count
