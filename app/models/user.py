from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.hostel import AdminHostelMapping, SupervisorHostelMapping
    from app.models.student import Student


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    HOSTEL_ADMIN = "hostel_admin"
    SUPERVISOR = "supervisor"
    STUDENT = "student"
    VISITOR = "visitor"


class OTPType(str, enum.Enum):
    REGISTRATION = "registration"
    PASSWORD_RESET = "password_reset"


class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), index=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships (lazy string refs avoid circular imports)
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    otp_verifications: Mapped[list[OTPVerification]] = relationship(
        "OTPVerification", back_populates="user", cascade="all, delete-orphan"
    )
    student_profile: Mapped[Student | None] = relationship(
        "Student", back_populates="user", uselist=False, foreign_keys="Student.user_id"
    )
    admin_hostel_mappings: Mapped[list[AdminHostelMapping]] = relationship(
        "AdminHostelMapping", back_populates="admin", foreign_keys="AdminHostelMapping.admin_id"
    )
    supervisor_hostel_mappings: Mapped[list[SupervisorHostelMapping]] = relationship(
        "SupervisorHostelMapping",
        back_populates="supervisor",
        foreign_keys="SupervisorHostelMapping.supervisor_id",
    )


class RefreshToken(BaseModel):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")


class OTPVerification(BaseModel):
    __tablename__ = "otp_verifications"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    otp_code_hash: Mapped[str] = mapped_column(String(255))
    otp_type: Mapped[OTPType] = mapped_column(Enum(OTPType))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship("User", back_populates="otp_verifications")
