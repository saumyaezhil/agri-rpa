from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, Document

from ..services.validator import (
    validate_application,
    calculate_score,
    make_decision
)


router = APIRouter(
    prefix="/api/applications",
    tags=["Verification"]
)


@router.post("/{application_id}/verify")
def verify_application(
    application_id: str,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------
    # 1. Find application
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
    # 2. Get uploaded documents
    # --------------------------------------------------

    documents = (
        db.query(Document)
        .filter(
            Document.application_id
            == application_id
        )
        .all()
    )

    if not documents:

        raise HTTPException(
            status_code=400,
            detail="No documents uploaded"
        )

    # --------------------------------------------------
    # 3. Run validation
    # --------------------------------------------------

    validation_results = validate_application(
        application,
        documents
    )

    # --------------------------------------------------
    # 4. Calculate score
    # --------------------------------------------------

    score = calculate_score(
        validation_results
    )

    # --------------------------------------------------
    # 5. Make decision
    # --------------------------------------------------

    decision = make_decision(
        score,
        validation_results
    )

    # --------------------------------------------------
    # 6. Update application
    # --------------------------------------------------

    application.verification_score = score

    application.decision = decision

    if decision == "AUTO_PROCESS":

        application.status = "AUTO_APPROVED"

    else:

        application.status = "HUMAN_REVIEW"

    # --------------------------------------------------
    # 7. Update document statuses
    # --------------------------------------------------

    for document in documents:

        if decision == "AUTO_PROCESS":

            document.verification_status = (
                "VERIFIED"
            )

        else:

            document.verification_status = (
                "REVIEW"
            )

    # --------------------------------------------------
    # 8. Save
    # --------------------------------------------------

    db.commit()

    db.refresh(application)

    # --------------------------------------------------
    # 9. Return verification report
    # --------------------------------------------------

    return {

        "application_id": application_id,

        "verification_score": score,

        "decision": decision,

        "status": application.status,

        "validation": validation_results

    }
