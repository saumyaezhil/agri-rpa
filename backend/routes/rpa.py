from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application


router = APIRouter(
    prefix="/api/rpa",
    tags=["RPA"]
)


@router.get("/next-application")
def get_next_application(
    db: Session = Depends(get_db)
):

    application = (
        db.query(Application)
        .filter(
            Application.decision == "AUTO_PROCESS"
        )
        .filter(
            Application.status == "AUTO_APPROVED"
        )
        .first()
    )

    if not application:
        return {
            "available": False,
            "message": "No application available for RPA processing"
        }

    application.status = "RPA_PROCESSING"

    db.commit()

    return {
        "available": True,
        "application_id": application.application_id,
        "farmer_name": application.farmer_name,
        "mobile": application.mobile,
        "service_type": application.service_type,
        "survey_number": application.survey_number,
        "village": application.village,
        "verification_score": application.verification_score
    }


@router.post("/{application_id}/complete")
def complete_rpa(
    application_id: str,
    government_application_id: str,
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

    application.government_application_id = (
        government_application_id
    )

    application.status = "SUBMITTED_TO_GOVERNMENT"

    db.commit()
    db.refresh(application)

    return {
        "message": "RPA processing completed",
        "application_id": application_id,
        "government_application_id":
            government_application_id,
        "status": application.status
    }


@router.post("/{application_id}/failed")
def fail_rpa(
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

    application.status = "HUMAN_REVIEW"

    db.commit()

    return {
        "message": "RPA processing failed",
        "application_id": application_id,
        "status": application.status
    }
