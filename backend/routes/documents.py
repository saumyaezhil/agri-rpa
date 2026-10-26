
import json
import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, Document
from ..services.ocr import extract_text
from ..services.document_classifier import classify_document
from ..services.extractor import extract_fields

router = APIRouter(prefix="/api/applications", tags=["Documents"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("backend/uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def safe_filename(filename: str) -> str:
    name = Path(filename or "upload").name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or "upload"


def find_application(db: Session, application_id: str):
    application = (
        db.query(Application)
        .filter(Application.application_id == application_id)
        .first()
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("/{application_id}/documents")
async def upload_document(
    application_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: Session = Depends(get_db),
):
    find_application(db, application_id)

    original_name = safe_filename(file.filename)
    extension = Path(original_name).suffix.lower()
    expected_type = document_type.strip().lower()

    if extension not in ALLOWED_EXTENSIONS:
        await file.close()
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a PDF or image.",
        )

    if not expected_type:
        await file.close()
        raise HTTPException(status_code=400, detail="Document type is required")

    application_dir = UPLOAD_DIR / application_id
    application_dir.mkdir(parents=True, exist_ok=True)

    # Unique names avoid collisions with previous uploads.
    filepath = application_dir / f"{uuid.uuid4().hex}_{original_name}"

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the 10 MB limit",
            )

        with filepath.open("wb") as output:
            output.write(content)
    finally:
        await file.close()

    try:
        # Actual signature: extract_text(filepath) -> (text, confidence)
        ocr_text, ocr_confidence = extract_text(str(filepath))
        ocr_text = str(ocr_text or "")
        ocr_confidence = float(ocr_confidence or 0.0)

        # Actual signature: classify_document(text, filename)
        detected_type = str(
            classify_document(ocr_text, original_name) or "unknown"
        ).strip().lower()

        # Actual signature: extract_fields(text, document_type)
        extracted_data = extract_fields(ocr_text, detected_type) or {}

        if detected_type == "unknown":
            verification_status = "REVIEW"
        elif detected_type != expected_type:
            verification_status = "TYPE_MISMATCH"
        elif ocr_confidence < 0.50:
            verification_status = "LOW_OCR_CONFIDENCE"
        else:
            verification_status = "PROCESSED"

        document = Document(
            application_id=application_id,
            filename=original_name,
            filepath=str(filepath),
            document_type=expected_type,
            ocr_text=ocr_text,
            ocr_confidence=ocr_confidence,
            extracted_data=json.dumps(extracted_data),
            verification_status=verification_status,
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return {
            "message": "Document uploaded and processed",
            "application_id": application_id,
            "document_id": document.id,
            "filename": original_name,
            "document_type": expected_type,
            "detected_type": detected_type,
            "verification_status": verification_status,
            "ocr_confidence": ocr_confidence,
            "extracted_data": extracted_data,
        }

    except Exception as error:
        db.rollback()
        # Keep the file for diagnosis instead of risking a Windows
        # file-lock cleanup error that masks the original exception.
        logger.exception(
            "OCR/document processing failed for application %s",
            application_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {error}",
        ) from error


@router.get("/{application_id}/documents")
def get_application_documents(
    application_id: str,
    db: Session = Depends(get_db),
):
    find_application(db, application_id)

    documents = (
        db.query(Document)
        .filter(Document.application_id == application_id)
        .all()
    )

    results = []
    for document in documents:
        try:
            extracted_data = json.loads(document.extracted_data or "{}")
        except (ValueError, TypeError):
            extracted_data = {}

        results.append({
            "document_id": document.id,
            "filename": document.filename,
            "document_type": document.document_type,
            "verification_status": document.verification_status,
            "ocr_confidence": document.ocr_confidence,
            "extracted_data": extracted_data,
        })

    return results


@router.get("/{application_id}/documents/{document_id}/download")
def download_document(
    application_id: str,
    document_id: int,
    db: Session = Depends(get_db),
):
    find_application(db, application_id)

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.application_id == application_id,
        )
        .first()
    )

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    filepath = Path(document.filepath)
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="Document file not found")

    return FileResponse(
        path=str(filepath),
        filename=document.filename,
        media_type="application/octet-stream",
    )
