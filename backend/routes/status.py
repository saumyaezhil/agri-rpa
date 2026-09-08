from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application


router = APIRouter(
    prefix="/api/status",
    tags=["Status"]
)


@router.get("/{application_id}")
def get_status(
    application_id: str,
    db: Session = Depends(get_db)
):

    application = (
        db.query(Application)
        .filter(
            Application.application_id == application_id
        )
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    return {
        "application_id": application.application_id,
        "farmer_name": application.farmer_name,
        "service": application.service_type,
        "status": application.status,
        "verification_score": application.verification_score,
        "decision": application.decision,
        "government_application_id":
            application.government_application_id,
        "created_at": application.created_at
    }
