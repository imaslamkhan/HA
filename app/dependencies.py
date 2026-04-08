from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: str
    role: str
    hostel_ids: set[str] = field(default_factory=set)


# ── Shared DB session dependency ─────────────────────────────────────────────
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    x_user_id: Annotated[str | None, Header()] = None,
    x_user_role: Annotated[str | None, Header()] = None,
    x_hostel_ids: Annotated[str | None, Header()] = None,
    db: DBSession = None,  # type: ignore[assignment]
) -> CurrentUser:
    """
    Dual-mode authentication:
    1. JWT Bearer token  — used by the React frontend
    2. x-user-* headers — used by seed scripts / internal tools / tests
    """
    # ── JWT Bearer path ───────────────────────────────────────────────
    if credentials and credentials.credentials:
        try:
            payload = decode_token(credentials.credentials)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id: str = payload.get("sub", "")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload.",
            )

        # Lazy imports to avoid circular dependency at module load time
        from app.models.hostel import AdminHostelMapping, SupervisorHostelMapping
        from app.models.user import User

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive.",
            )

        role: str = user.role.value if hasattr(user.role, "value") else str(user.role)
        hostel_ids: set[str] = set()

        if role == "hostel_admin":
            r = await db.execute(
                select(AdminHostelMapping.hostel_id).where(
                    AdminHostelMapping.admin_id == user_id
                )
            )
            hostel_ids = {str(hid) for hid in r.scalars().all()}
        elif role == "supervisor":
            r = await db.execute(
                select(SupervisorHostelMapping.hostel_id).where(
                    SupervisorHostelMapping.supervisor_id == user_id
                )
            )
            hostel_ids = {str(hid) for hid in r.scalars().all()}

        return CurrentUser(id=user_id, role=role, hostel_ids=hostel_ids)

    # ── Header path (seed / tests) ────────────────────────────────────
    if x_user_id and x_user_role:
        return CurrentUser(
            id=x_user_id,
            role=x_user_role,
            hostel_ids=set(filter(None, (x_hostel_ids or "").split(","))),
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_roles(*allowed_roles: str):
    """Role-based access control decorator for route handlers."""

    async def checker(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not permitted here.",
            )
        return current_user

    return checker
