import os
import json
import shutil

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException
)

from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, Document

from ..services.ocr import extract_text
from ..services.document_classifier import classify_document
from ..services.extractor import extract_fields


router = APIRouter(
    prefix="/api/applications",
    tags=["Documents"]
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

UPLOAD_DIR = "backend/uploads"

ALLOWED_DOCUMENT_TYPES = {
    "identity_proof",
    "land_record",
    "address_proof"
}

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg"
}


# Create upload directory
os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ---------------------------------------------------------
# Upload Document
# ---------------------------------------------------------

@router.post("/{application_id}/documents")
def upload_document(
    application_id: str,
    document_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Check application exists
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # 2. Validate document type
    # -----------------------------------------------------

    if document_type not in ALLOWED_DOCUMENT_TYPES:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid document type. "
                "Use identity_proof, "
                "land_record, or address_proof."
            )
        )


    # -----------------------------------------------------
    # 3. Validate file extension
    # -----------------------------------------------------

    extension = os.path.splitext(
        file.filename
    )[1].lower()

    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only PDF, PNG, JPG and JPEG "
                "files are allowed."
            )
        )


    # -----------------------------------------------------
    # 4. Create application-specific folder
    # -----------------------------------------------------

    application_dir = os.path.join(
        UPLOAD_DIR,
        application_id
    )

    os.makedirs(
        application_dir,
        exist_ok=True
    )


    # -----------------------------------------------------
    # 5. Save uploaded file
    # -----------------------------------------------------

    filepath = os.path.join(
        application_dir,
        file.filename
    )

    try:

        with open(filepath, "wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to save uploaded file: "
                + str(error)
            )
        )


    # -----------------------------------------------------
    # 6. Run OCR
    # -----------------------------------------------------

    try:

        ocr_text = extract_text(
            filepath
        )

    except Exception as error:

        # Remove file if OCR fails
        if os.path.exists(filepath):
            os.remove(filepath)

        raise HTTPException(
            status_code=500,
            detail=(
                "OCR processing failed: "
                + str(error)
            )
        )


    # -----------------------------------------------------
    # 7. Classify document
    # -----------------------------------------------------

    detected_type = classify_document(
        ocr_text,
        file.filename
    )


    # -----------------------------------------------------
    # 8. Extract structured information
    # -----------------------------------------------------

    extracted_data = extract_fields(
        ocr_text,
        detected_type
    )


    # -----------------------------------------------------
    # 9. Determine OCR confidence
    # -----------------------------------------------------

    # For the current prototype we use a placeholder
    # confidence value.
    #
    # Later this will be calculated from OCR quality.

    ocr_confidence = 0.95


    # -----------------------------------------------------
    # 10. Check classification
    # -----------------------------------------------------

    classification_status = "OCR_COMPLETED"

    if detected_type == "unknown":

        classification_status = "CLASSIFICATION_REVIEW"


    # -----------------------------------------------------
    # 11. Store document in database
    # -----------------------------------------------------

    document = Document(

        application_id=application_id,

        document_type=document_type,

        filename=file.filename,

        filepath=filepath,

        ocr_text=ocr_text,

        ocr_confidence=ocr_confidence,

        extracted_data=json.dumps(
            extracted_data
        ),

        verification_status=classification_status
    )


    db.add(document)

    db.commit()

    db.refresh(document)


    # -----------------------------------------------------
    # 12. Return result
    # -----------------------------------------------------

    return {

        "message": "Document uploaded and processed",

        "application_id": application_id,

        "document_id": document.id,

        "document_type": document_type,

        "detected_document_type": detected_type,

        "filename": file.filename,

        "ocr_confidence": ocr_confidence,

        "verification_status": (
            document.verification_status
        ),

        "extracted_data": extracted_data,

        "ocr_text": ocr_text
    }


# ---------------------------------------------------------
# Get Documents
# ---------------------------------------------------------

@router.get("/{application_id}/documents")
def get_documents(
    application_id: str,
    db: Session = Depends(get_db)
):

    # Check application
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


    result = []


    for document in documents:

        try:

            extracted_data = json.loads(
                document.extracted_data
            ) if document.extracted_data else {}

        except Exception:

            extracted_data = {}


        result.append({

            "document_id": document.id,

            "document_type": document.document_type,

            "filename": document.filename,

            "verification_status": (
                document.verification_status
            ),

            "ocr_confidence": (
                document.ocr_confidence
            ),

            "extracted_data": extracted_data
        })


    return result
