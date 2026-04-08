from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import MaintenanceRequest
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.maintenance_repository import MaintenanceRepository
from app.schemas.maintenance import MaintenanceCreateRequest, MaintenanceUpdateRequest


class MaintenanceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.maintenance = MaintenanceRepository(session)
        self.assignments = AssignmentRepository(session)

    async def list_supervisor_requests(self, *, supervisor_id: str):
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        requests: list[MaintenanceRequest] = []
        for hostel_id in hostel_ids:
            requests.extend(await self.maintenance.list_by_hostel(hostel_id))
        return requests

    async def create_supervisor_request(
        self, *, supervisor_id: str, payload: MaintenanceCreateRequest
    ) -> MaintenanceRequest:
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        if not hostel_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No hostel assigned.")

        requires_admin_approval = (
            payload.estimated_cost is not None and payload.estimated_cost >= 5000
        )
        request = MaintenanceRequest(
            hostel_id=hostel_ids[0],
            room_id=payload.room_id,
            reported_by=supervisor_id,
            category=payload.category,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            status="open",
            estimated_cost=payload.estimated_cost,
            requires_admin_approval=requires_admin_approval,
        )
        request = await self.maintenance.create(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def update_supervisor_request(
        self, *, supervisor_id: str, request_id: str, payload: MaintenanceUpdateRequest
    ) -> MaintenanceRequest:
        request = await self.maintenance.get_by_id(request_id)
        if request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
        hostel_ids = await self.assignments.get_supervisor_hostel_ids(supervisor_id)
        if str(request.hostel_id) not in hostel_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No hostel access.")

        if payload.status is not None:
            request.status = payload.status
        if payload.estimated_cost is not None:
            request.estimated_cost = payload.estimated_cost
        if payload.actual_cost is not None:
            request.actual_cost = payload.actual_cost
        if payload.assigned_vendor_name is not None:
            request.assigned_vendor_name = payload.assigned_vendor_name
        if payload.vendor_contact is not None:
            request.vendor_contact = payload.vendor_contact
        if payload.requires_admin_approval is not None:
            request.requires_admin_approval = payload.requires_admin_approval
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def list_admin_requests(self, *, hostel_id: str):
        return await self.maintenance.list_by_hostel(hostel_id)

    async def approve_admin_request(self, *, actor_id: str, request_id: str) -> MaintenanceRequest:
        request = await self.maintenance.get_by_id(request_id)
        if request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
        request.requires_admin_approval = False
        request.approved_by = actor_id
        request.status = "approved"
        await self.session.commit()
        await self.session.refresh(request)
        return request
