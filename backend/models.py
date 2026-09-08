from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text
)

from datetime import datetime

from .database import Base


# =========================================================
# APPLICATION
# =========================================================

class Application(Base):

    __tablename__ = "applications"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    application_id = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )


    farmer_name = Column(
        String,
        nullable=False
    )


    mobile = Column(
        String,
        nullable=False
    )


    service_type = Column(
        String,
        nullable=False
    )


    survey_number = Column(
        String,
        nullable=False
    )


    village = Column(
        String,
        nullable=False
    )


    status = Column(
        String,
        default="DOCUMENT_VERIFICATION"
    )


    verification_score = Column(
        Float,
        default=0.0
    )


    decision = Column(
        String,
        default="PENDING"
    )


    government_application_id = Column(
        String,
        nullable=True
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# =========================================================
# DOCUMENT
# =========================================================

class Document(Base):

    __tablename__ = "documents"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    application_id = Column(
        String,
        ForeignKey(
            "applications.application_id"
        ),
        nullable=False
    )


    document_type = Column(
        String,
        nullable=False
    )


    filename = Column(
        String,
        nullable=False
    )


    filepath = Column(
        String,
        nullable=False
    )


    # Raw OCR output
    ocr_text = Column(
        Text,
        nullable=True
    )


    # OCR confidence
    ocr_confidence = Column(
        Float,
        default=0.0
    )


    # Structured information extracted
    # from the document.
    #
    # Stored as JSON string in SQLite.

    extracted_data = Column(
        Text,
        nullable=True
    )


    verification_status = Column(
        String,
        default="PENDING"
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
