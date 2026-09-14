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

from ..models import (
    Application,
    Document
)

from ..services.ocr import (
    extract_text
)

from ..services.document_classifier import (
    classify_document
)

from ..services.extractor import (
    extract_fields
)


router = APIRouter(
    prefix="/api/applications",
    tags=["Documents"]
)


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


os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


@router.post(
    "/{application_id}/documents"
)
def upload_document(
    application_id: str,
    document_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # --------------------------------------------------
    # 1. Check application
    # --------------------------------------------------

    application = (
        db.query(Application)
        .filter(
            Application.application_id
            == application_id
        )
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )


    # --------------------------------------------------
    # 2. Validate document type
    # --------------------------------------------------

    if document_type not in ALLOWED_DOCUMENT_TYPES:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid document type. "
                "Use identity_proof, "
                "land_record, or "
                "address_proof."
            )
        )


    # --------------------------------------------------
    # 3. Validate file extension
    # --------------------------------------------------

    extension = (
        os.path.splitext(
            file.filename
        )[1]
        .lower()
    )

    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only PDF, PNG, JPG and "
                "JPEG files are allowed."
            )
        )


    # --------------------------------------------------
    # 4. Create application upload directory
    # --------------------------------------------------

    application_dir = os.path.join(
        UPLOAD_DIR,
        application_id
    )

    os.makedirs(
        application_dir,
        exist_ok=True
    )


    # --------------------------------------------------
    # 5. Save uploaded document
    # --------------------------------------------------

    filepath = os.path.join(
        application_dir,
        file.filename
    )

    try:

        with open(
            filepath,
            "wb"
        ) as buffer:

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


    # --------------------------------------------------
    # 6. Run OCR
    # --------------------------------------------------

    try:

        ocr_result = extract_text(
            filepath
        )

        # The OCR service returns:
        #
        # (
        #     extracted_text,
        #     confidence
        # )
        #
        # Explicitly unpack it here.

        if (
            isinstance(
                ocr_result,
                tuple
            )
            and len(ocr_result) == 2
        ):

            ocr_text = ocr_result[0]
            ocr_confidence = ocr_result[1]

        else:

            # Defensive fallback in case
            # an older OCR implementation
            # returns only text.

            ocr_text = str(
                ocr_result
            )

            ocr_confidence = 0.0


    except Exception as error:

        if os.path.exists(filepath):

            os.remove(filepath)

        raise HTTPException(
            status_code=500,
            detail=(
                "OCR processing failed: "
                + str(error)
            )
        )


    # --------------------------------------------------
    # 7. Make absolutely sure classifier
    #    receives text, not a tuple
    # --------------------------------------------------

    if not isinstance(
        ocr_text,
        str
    ):

        ocr_text = str(
            ocr_text
        )


    # --------------------------------------------------
    # 8. Classify document
    # --------------------------------------------------

    detected_type = classify_document(
        ocr_text,
        file.filename
    )


    # --------------------------------------------------
    # 9. Determine verification status
    # --------------------------------------------------

    if detected_type == "unknown":

        verification_status = (
            "CLASSIFICATION_REVIEW"
        )

    elif detected_type != document_type:

        verification_status = (
            "TYPE_MISMATCH"
        )

    elif ocr_confidence < 0.50:

        verification_status = (
            "LOW_OCR_CONFIDENCE"
        )

    else:

        verification_status = (
            "OCR_COMPLETED"
        )


    # --------------------------------------------------
    # 10. Extract fields
    # --------------------------------------------------

    extracted_data = extract_fields(
        ocr_text,
        detected_type
    )


    # --------------------------------------------------
    # 11. Store document in database
    # --------------------------------------------------

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

        verification_status=(
            verification_status
        )
    )


    db.add(
        document
    )

    db.commit()

    db.refresh(
        document
    )


    # --------------------------------------------------
    # 12. Return processing result
    # --------------------------------------------------

    return {

        "message":
            "Document uploaded and processed",

        "application_id":
            application_id,

        "document_id":
            document.id,

        "document_type":
            document_type,

        "detected_document_type":
            detected_type,

        "filename":
            file.filename,

        "ocr_confidence":
            round(
                ocr_confidence,
                3
            ),

        "verification_status":
            verification_status,

        "extracted_data":
            extracted_data,

        "ocr_text":
            ocr_text
    }


# ======================================================
# GET DOCUMENTS
# ======================================================

@router.get(
    "/{application_id}/documents"
)
def get_documents(
    application_id: str,
    db: Session = Depends(get_db)
):

    application = (
        db.query(Application)
        .filter(
            Application.application_id
            == application_id
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
            Document.application_id
            == application_id
        )
        .all()
    )


    result = []


    for document in documents:

        try:

            extracted_data = (

                json.loads(
                    document.extracted_data
                )

                if document.extracted_data

                else {}

            )

        except Exception:

            extracted_data = {}


        result.append({

            "document_id":
                document.id,

            "document_type":
                document.document_type,

            "filename":
                document.filename,

            "verification_status":
                document.verification_status,

            "ocr_confidence":
                document.ocr_confidence,

            "extracted_data":
                extracted_data
        })


    return result
