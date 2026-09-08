from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application
from ..schemas import ApplicationCreate, ApplicationResponse


router = APIRouter(
    prefix="/api/applications",
    tags=["Applications"]
)


def generate_application_id(db: Session):
    count = db.query(Application).count() + 1
    return f"AGR-{count:05d}"


@router.post(
    "",
    response_model=ApplicationResponse
)
def create_application(
    application: ApplicationCreate,
    db: Session = Depends(get_db)
):

    application_id = generate_application_id(db)

    new_application = Application(
        application_id=application_id,
        farmer_name=application.farmer_name,
        mobile=application.mobile,
        service_type=application.service_type,
        survey_number=application.survey_number,
        village=application.village,
        status="DOCUMENT_VERIFICATION",
        verification_score=0.0,
        decision="PENDING"
    )

    db.add(new_application)
    db.commit()
    db.refresh(new_application)

    return new_application


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse
)
def get_application(
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

    return application


@router.get(
    "",
    response_model=List[ApplicationResponse]
)
def get_applications(
    db: Session = Depends(get_db)
):

    return db.query(Application).all()

