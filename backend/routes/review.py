from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, Document


router = APIRouter(
    prefix="/api/review",
    tags=["Human Review"]
)


# --------------------------------------------------
# GET HUMAN REVIEW QUEUE
# --------------------------------------------------

@router.get("/queue")
def get_review_queue(
    db: Session = Depends(get_db)
):

    applications = (
        db.query(Application)
        .filter(
            Application.status == "HUMAN_REVIEW"
        )
        .order_by(
            Application.created_at.asc()
        )
        .all()
    )

    return {
        "count": len(applications),
        "applications": [
            {
                "application_id": application.application_id,
                "farmer_name": application.farmer_name,
                "mobile": application.mobile,
                "service_type": application.service_type,
                "survey_number": application.survey_number,
                "village": application.village,
                "status": application.status,
                "verification_score": application.verification_score,
                "decision": application.decision,
                "created_at": application.created_at
            }
            for application in applications
        ]
    }


# --------------------------------------------------
# GET APPLICATION FOR REVIEW
# --------------------------------------------------

@router.get("/{application_id}")
def get_application_for_review(
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

    documents = (
        db.query(Document)
        .filter(
            Document.application_id == application_id
        )
        .all()
    )

    return {
        "application": {
            "application_id": application.application_id,
            "farmer_name": application.farmer_name,
            "mobile": application.mobile,
            "service_type": application.service_type,
            "survey_number": application.survey_number,
            "village": application.village,
            "status": application.status,
            "verification_score": application.verification_score,
            "decision": application.decision,
            "government_application_id":
                application.government_application_id
        },
        "documents": [
            {
                "document_id": document.id,
                "document_type": document.document_type,
                "filename": document.filename,
                "ocr_confidence": document.ocr_confidence,
                "ocr_text": document.ocr_text,
                "extracted_data": document.extracted_data,
                "verification_status":
                    document.verification_status
            }
            for document in documents
        ]
    }


# --------------------------------------------------
# APPROVE APPLICATION
# --------------------------------------------------

@router.post("/{application_id}/approve")
def approve_application(
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

    if application.status != "HUMAN_REVIEW":
        raise HTTPException(
            status_code=400,
            detail=(
                "Application is not in human review. "
                "Current status: "
                + application.status
            )
        )

    # Human officer has approved the application.
    application.decision = "AUTO_PROCESS"
    application.status = "AUTO_APPROVED"

    db.commit()
    db.refresh(application)

    return {
        "message": "Application approved by officer",
        "application_id": application.application_id,
        "decision": application.decision,
        "status": application.status
    }


# --------------------------------------------------
# REJECT APPLICATION
# --------------------------------------------------

@router.post("/{application_id}/reject")
def reject_application(
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

    if application.status != "HUMAN_REVIEW":
        raise HTTPException(
            status_code=400,
            detail=(
                "Application is not in human review. "
                "Current status: "
                + application.status
            )
        )

    application.decision = "REJECTED"
    application.status = "REJECTED"

    db.commit()
    db.refresh(application)

    return {
        "message": "Application rejected by officer",
        "application_id": application.application_id,
        "decision": application.decision,
        "status": application.status
    }
