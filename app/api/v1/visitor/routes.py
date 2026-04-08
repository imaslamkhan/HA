from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, DBSession, require_roles
from app.models.booking import Booking, BookingStatus
from app.models.hostel import Hostel
from app.models.operations import Review
from app.models.user import User
from app.schemas.booking import BookingResponse, BookingCancellationRequest
from app.schemas.base import APIModel, TimestampedResponse

router = APIRouter()
VisitorUser = Annotated[CurrentUser, Depends(require_roles("visitor", "student", "hostel_admin", "supervisor", "super_admin"))]


# ── Schemas ──────────────────────────────────────────────────────────────────

class VisitorProfileResponse(APIModel):
    id: str
    email: str
    phone: str
    full_name: str
    role: str
    profile_picture_url: str | None = None
    is_email_verified: bool
    is_phone_verified: bool


class VisitorProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=8, max_length=30)
    profile_picture_url: str | None = None


class ReviewCreateRequest(BaseModel):
    hostel_id: str
    booking_id: str | None = None
    overall_rating: float = Field(ge=1, le=5)
    cleanliness_rating: float = Field(ge=1, le=5)
    food_rating: float = Field(ge=1, le=5)
    security_rating: float = Field(ge=1, le=5)
    value_rating: float = Field(ge=1, le=5)
    title: str = Field(min_length=3, max_length=255)
    content: str = Field(min_length=10)


class ReviewResponse(TimestampedResponse):
    id: str
    hostel_id: str
    visitor_id: str
    overall_rating: float
    cleanliness_rating: float
    food_rating: float
    security_rating: float
    value_rating: float
    title: str
    content: str
    is_verified: bool
    is_published: bool


class FavoriteResponse(APIModel):
    hostel_id: str
    hostel_name: str
    hostel_slug: str
    city: str
    hostel_type: str
    starting_price: float


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=VisitorProfileResponse)
async def get_profile(current_user: VisitorUser, db: DBSession):
    """**Get visitor profile.**"""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.patch("/profile", response_model=VisitorProfileResponse)
async def update_profile(payload: VisitorProfileUpdateRequest, current_user: VisitorUser, db: DBSession):
    """**Update visitor profile** — name, phone, profile picture."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.profile_picture_url is not None:
        user.profile_picture_url = payload.profile_picture_url
    await db.commit()
    await db.refresh(user)
    return user


# ── Bookings ──────────────────────────────────────────────────────────────────

@router.get("/bookings", response_model=list[BookingResponse])
async def list_bookings(current_user: VisitorUser, db: DBSession):
    """**List all bookings for the authenticated visitor.**"""
    result = await db.execute(
        select(Booking).where(Booking.visitor_id == current_user.id).order_by(Booking.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(booking_id: str, payload: BookingCancellationRequest, current_user: VisitorUser, db: DBSession):
    """**Cancel a booking.** Only allowed for payment_pending or pending_approval status."""
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if str(booking.visitor_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your booking.")
    if booking.status not in (BookingStatus.PAYMENT_PENDING, BookingStatus.PENDING_APPROVAL):
        raise HTTPException(status_code=400, detail=f"Cannot cancel booking in '{booking.status.value}' status.")
    booking.status = BookingStatus.CANCELLED
    booking.cancellation_reason = payload.reason
    await db.commit()
    await db.refresh(booking)
    return booking


# ── Reviews ───────────────────────────────────────────────────────────────────

@router.post("/reviews", response_model=ReviewResponse, status_code=201)
async def submit_review(payload: ReviewCreateRequest, current_user: VisitorUser, db: DBSession):
    """**Submit a review for a hostel.** One review per visitor per hostel."""
    # Check for duplicate
    existing = await db.execute(
        select(Review).where(Review.visitor_id == current_user.id, Review.hostel_id == payload.hostel_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already reviewed this hostel.")
    if payload.booking_id:
        booking_result = await db.execute(select(Booking).where(Booking.id == payload.booking_id))
        booking = booking_result.scalar_one_or_none()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")
        if str(booking.visitor_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not your booking.")
        if str(booking.hostel_id) != payload.hostel_id:
            raise HTTPException(status_code=400, detail="Booking does not belong to this hostel.")
        if booking.status != BookingStatus.CHECKED_OUT:
            raise HTTPException(status_code=400, detail="Reviews are allowed only after checkout.")
    else:
        booking_result = await db.execute(
            select(Booking)
            .where(
                Booking.visitor_id == current_user.id,
                Booking.hostel_id == payload.hostel_id,
                Booking.status == BookingStatus.CHECKED_OUT,
            )
            .order_by(Booking.check_out_date.desc())
        )
        checked_out_booking = booking_result.scalars().first()
        if not checked_out_booking:
            raise HTTPException(status_code=400, detail="You can review this hostel only after checkout.")
    review = Review(
        visitor_id=current_user.id,
        hostel_id=payload.hostel_id,
        booking_id=payload.booking_id,
        overall_rating=payload.overall_rating,
        cleanliness_rating=payload.cleanliness_rating,
        food_rating=payload.food_rating,
        security_rating=payload.security_rating,
        value_rating=payload.value_rating,
        title=payload.title,
        content=payload.content,
        is_verified=False,
        is_published=True,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


@router.get("/reviews", response_model=list[ReviewResponse])
async def list_my_reviews(current_user: VisitorUser, db: DBSession):
    """**List all reviews submitted by the visitor.**"""
    result = await db.execute(
        select(Review).where(Review.visitor_id == current_user.id).order_by(Review.created_at.desc())
    )
    return list(result.scalars().all())


# ── Favorites ─────────────────────────────────────────────────────────────────

@router.get("/favorites", response_model=list[FavoriteResponse])
async def list_favorites(current_user: VisitorUser, db: DBSession):
    """**List saved/favorite hostels.**"""
    from app.models.hostel import VisitorFavorite
    result = await db.execute(
        select(Hostel)
        .join(VisitorFavorite, VisitorFavorite.hostel_id == Hostel.id)
        .where(VisitorFavorite.visitor_id == current_user.id)
        .order_by(VisitorFavorite.created_at.desc())
    )
    hostels = result.scalars().all()
    return [
        FavoriteResponse(
            hostel_id=str(h.id),
            hostel_name=h.name,
            hostel_slug=h.slug,
            city=h.city,
            hostel_type=h.hostel_type,
            starting_price=0.0,
        )
        for h in hostels
    ]


@router.post("/favorites/{hostel_id}", status_code=201)
async def add_favorite(hostel_id: str, current_user: VisitorUser, db: DBSession):
    """**Save a hostel to favorites.**"""
    from app.models.hostel import VisitorFavorite
    existing = await db.execute(
        select(VisitorFavorite).where(
            VisitorFavorite.visitor_id == current_user.id,
            VisitorFavorite.hostel_id == hostel_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Already in favorites."}
    db.add(VisitorFavorite(visitor_id=current_user.id, hostel_id=hostel_id))
    await db.commit()
    return {"message": "Added to favorites.", "hostel_id": hostel_id}


@router.delete("/favorites/{hostel_id}", status_code=200)
async def remove_favorite(hostel_id: str, current_user: VisitorUser, db: DBSession):
    """**Remove a hostel from favorites.**"""
    from app.models.hostel import VisitorFavorite
    result = await db.execute(
        select(VisitorFavorite).where(
            VisitorFavorite.visitor_id == current_user.id,
            VisitorFavorite.hostel_id == hostel_id,
        )
    )
    fav = result.scalar_one_or_none()
    if fav:
        await db.delete(fav)
        await db.commit()
    return {"message": "Removed from favorites.", "hostel_id": hostel_id}
