import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, Document


router = APIRouter(prefix="/api/rpa", tags=["RPA"])


# ==========================================================
# GET NEXT APPLICATION
# ==========================================================

@router.get("/next-application")
def get_next_application(db: Session = Depends(get_db)):

    application = (
        db.query(Application)
        .filter(Application.decision == "AUTO_PROCESS")
        .filter(Application.status == "AUTO_APPROVED")
        .first()
    )

    if not application:
        return {
            "available": False,
            "message": "No application available for RPA processing"
        }

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


# ==========================================================
# START RPA PROCESSING
# ==========================================================

@router.post("/{application_id}/start")
def start_rpa(
    application_id: str,
    db: Session = Depends(get_db)
):

    application = (
        db.query(Application)
        .filter(Application.application_id == application_id)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    if application.decision != "AUTO_PROCESS":
        raise HTTPException(
            status_code=400,
            detail="Application is not eligible for RPA processing"
        )

    if application.status != "AUTO_APPROVED":
        raise HTTPException(
            status_code=400,
            detail=(
                "Application is not ready to start RPA. "
                "Current status: " + application.status
            )
        )

    application.status = "RPA_PROCESSING"

    db.commit()
    db.refresh(application)

    return {
        "message": "RPA processing started",
        "application_id": application.application_id,
        "status": application.status
    }


# ==========================================================
# GET RPA DOCUMENTS
# ==========================================================

@router.get("/{application_id}/documents")
def get_rpa_documents(
    application_id: str,
    db: Session = Depends(get_db)
):

    application = (
        db.query(Application)
        .filter(Application.application_id == application_id)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    documents = (
        db.query(Document)
        .filter(Document.application_id == application_id)
        .all()
    )

    if not documents:
        raise HTTPException(
            status_code=404,
            detail="No documents found for this application"
        )

    return {
        "application_id": application_id,
        "documents": [
            {
                "document_id": document.id,
                "document_type": document.document_type,
                "filename": document.filename,
                "filepath": document.filepath
            }
            for document in documents
        ]
    }


# ==========================================================
# DOWNLOAD DOCUMENT
# ==========================================================

@router.get("/{application_id}/documents/{document_id}/download")
def download_rpa_document(
    application_id: str,
    document_id: int,
    db: Session = Depends(get_db)
):

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.application_id == application_id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    if not os.path.isfile(document.filepath):
        raise HTTPException(
            status_code=404,
            detail="Document file not found"
        )

    return FileResponse(
        path=document.filepath,
        filename=document.filename,
        media_type="application/pdf"
    )


# ==========================================================
# COMPLETE RPA
# ==========================================================

@router.post("/{application_id}/complete")
def complete_rpa(
    application_id: str,
    government_application_id: str,
    db: Session = Depends(get_db)
):

    application = (
        db.query(Application)
        .filter(Application.application_id == application_id)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    if application.status != "RPA_PROCESSING":
        raise HTTPException(
            status_code=400,
            detail=(
                "Application is not currently being processed by RPA. "
                "Current status: " + application.status
            )
        )

    if not government_application_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Government application ID is required"
        )

    application.government_application_id = (
        government_application_id.strip()
    )

    application.status = "SUBMITTED_TO_GOVERNMENT"

    db.commit()
    db.refresh(application)

    return {
        "message": "RPA processing completed",
        "application_id": application_id,
        "government_application_id":
            application.government_application_id,
        "status": application.status
    }


# ==========================================================
# RPA FAILURE
# ==========================================================

@router.post("/{application_id}/failed")
def fail_rpa(
    application_id: str,
    db: Session = Depends(get_db)
):

    application = (
        db.query(Application)
        .filter(Application.application_id == application_id)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    if application.status != "RPA_PROCESSING":
        raise HTTPException(
            status_code=400,
            detail=(
                "Application is not currently being processed by RPA. "
                "Current status: " + application.status
            )
        )

    application.status = "HUMAN_REVIEW"

    db.commit()
    db.refresh(application)

    return {
        "message": "RPA processing failed",
        "application_id": application_id,
        "status": application.status
    }
