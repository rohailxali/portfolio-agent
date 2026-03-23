import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.session import get_db
from app.db.models import Lead, Appointment
from app.dependencies import require_owner
from app.db.models import User

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


class LeadSubmission(BaseModel):
    name: str
    email: EmailStr
    message: str | None = None
    source: str | None = "contact_form"


class LeadStatusUpdate(BaseModel):
    status: str


class AppointmentCreate(BaseModel):
    scheduled_at: str | None = None
    notes: str | None = None


@router.post("", status_code=201)
@limiter.limit("5/minute")
async def submit_lead(
    request: Request,
    body: LeadSubmission,
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint — ingests contact form submissions.
    Rate-limited to 5/minute per IP to prevent spam.
    """
    lead = Lead(
        name=body.name.strip(),
        email=body.email.lower().strip(),
        message=body.message,
        source=body.source,
        status="new",
    )
    db.add(lead)
    await db.flush()

    logger.info(f"New lead: id={lead.id} email={lead.email}")

    # Async: trigger classification + notification (best effort)
    try:
        from app.notifications.slack import send_slack_notification
        from app.config import get_settings
        settings = get_settings()
        if settings.slack_webhook_url:
            import asyncio
            asyncio.create_task(
                send_slack_notification(
                    subject="📬 New Lead",
                    body=f"Name: {lead.name}\nEmail: {lead.email}\nMessage: {lead.message or '—'}",
                )
            )
    except Exception as e:
        logger.warning(f"Lead notification failed (non-fatal): {e}")

    return {"id": str(lead.id), "status": "received"}


@router.get("")
async def list_leads(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    query = select(Lead).order_by(desc(Lead.created_at))
    if status:
        query = query.where(Lead.status == status)
    query = query.offset((page - 1) * page_size).limit(min(page_size, 100))

    result = await db.execute(query)
    leads = result.scalars().all()
    return [
        {
            "id": str(lead_item.id),
            "name": lead_item.name,
            "email": lead_item.email,
            "message": lead_item.message,
            "status": lead_item.status,
            "classification": lead_item.classification,
            "source": lead_item.source,
            "created_at": lead_item.created_at.isoformat(),
        }
        for lead_item in leads
    ]


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {
        "id": str(lead.id),
        "name": lead.name,
        "email": lead.email,
        "message": lead.message,
        "status": lead.status,
        "classification": lead.classification,
        "source": lead.source,
        "meta": lead.meta,
        "created_at": lead.created_at.isoformat(),
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: str,
    body: LeadStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    valid_statuses = {"new", "classified", "contacted", "converted", "spam"}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = body.status
    await db.flush()
    return {"id": lead_id, "status": lead.status}


@router.post("/{lead_id}/classify")
async def classify_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    from app.tools.leads import ClassifyLeadTool
    tool = ClassifyLeadTool()
    result = await tool.run(
        inputs={"lead_id": lead_id},
        db=db,
        user_id=str(current_user.id),
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data


@router.post("/{lead_id}/appointment", status_code=201)
async def create_appointment(
    lead_id: str,
    body: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    from datetime import datetime
    scheduled = None
    if body.scheduled_at:
        try:
            scheduled = datetime.fromisoformat(str(body.scheduled_at))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid scheduled_at format. Use ISO 8601.")

    appt = Appointment(
        lead_id=lead_id,
        scheduled_at=scheduled,
        notes=body.notes,
        status="pending",
    )
    db.add(appt)
    await db.flush()

    return {
        "appointment_id": str(appt.id),
        "lead_id": lead_id,
        "scheduled_at": scheduled.isoformat() if scheduled else None,
        "status": appt.status,
    }