from fastapi import HTTPException, status


def ensure_hostel_access(current_role: str, current_hostel_ids: set[str], hostel_id: str) -> None:
    if current_role == "super_admin":
        return
    if hostel_id not in current_hostel_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this hostel.",
        )
