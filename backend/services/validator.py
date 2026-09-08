import json
from typing import Dict, List, Any


REQUIRED_DOCUMENTS = [
    "identity_proof",
    "land_record",
    "address_proof"
]


def normalize(value):
    """Normalize text before comparison."""

    if value is None:
        return ""

    value = str(value).lower().strip()

    # Remove common punctuation
    for character in [",", ".", "-", "_"]:
        value = value.replace(character, " ")

    return " ".join(value.split())


def names_match(name1, name2):
    """Compare two names after normalization."""

    return normalize(name1) == normalize(name2)


def values_match(value1, value2):
    """Generic normalized value comparison."""

    return normalize(value1) == normalize(value2)


def get_extracted_data(document):
    """Read JSON extracted data from a document."""

    if not document.extracted_data:
        return {}

    try:
        return json.loads(document.extracted_data)
    except Exception:
        return {}


def validate_application(application, documents):
    """
    Validate application against OCR-extracted document data.
    """

    results = {
        "documents_complete": False,
        "name_match": False,
        "survey_match": False,
        "village_match": False,
        "ocr_quality": True,
        "issues": [],
        "document_details": []
    }

    # --------------------------------------------------
    # 1. Required documents
    # --------------------------------------------------

    uploaded_types = {
        document.document_type
        for document in documents
    }

    missing_documents = [
        document_type
        for document_type in REQUIRED_DOCUMENTS
        if document_type not in uploaded_types
    ]

    if not missing_documents:

        results["documents_complete"] = True

    else:

        results["issues"].append(
            "Missing documents: "
            + ", ".join(missing_documents)
        )

    # --------------------------------------------------
    # 2. OCR quality
    # --------------------------------------------------

    for document in documents:

        if document.ocr_confidence < 0.50:

            results["ocr_quality"] = False

            results["issues"].append(
                "Low OCR confidence for "
                + document.document_type
            )

    # --------------------------------------------------
    # 3. Extract document data
    # --------------------------------------------------

    identity_document = next(
        (
            document
            for document in documents
            if document.document_type == "identity_proof"
        ),
        None
    )

    land_document = next(
        (
            document
            for document in documents
            if document.document_type == "land_record"
        ),
        None
    )

    address_document = next(
        (
            document
            for document in documents
            if document.document_type == "address_proof"
        ),
        None
    )

    identity_data = get_extracted_data(
        identity_document
    ) if identity_document else {}

    land_data = get_extracted_data(
        land_document
    ) if land_document else {}

    address_data = get_extracted_data(
        address_document
    ) if address_document else {}

    # --------------------------------------------------
    # 4. NAME VALIDATION
    # --------------------------------------------------

    names_to_compare = []

    if application.farmer_name:
        names_to_compare.append(
            (
                "application",
                application.farmer_name
            )
        )

    if identity_data.get("name"):
        names_to_compare.append(
            (
                "identity_proof",
                identity_data.get("name")
            )
        )

    if land_data.get("name"):
        names_to_compare.append(
            (
                "land_record",
                land_data.get("name")
            )
        )

    if address_data.get("name"):
        names_to_compare.append(
            (
                "address_proof",
                address_data.get("name")
            )
        )

    if len(names_to_compare) >= 2:

        reference_name = names_to_compare[0][1]

        mismatched_names = []

        for source, name in names_to_compare[1:]:

            if not names_match(
                reference_name,
                name
            ):
                mismatched_names.append(
                    source
                )

        if not mismatched_names:

            results["name_match"] = True

        else:

            results["issues"].append(
                "Name mismatch detected in: "
                + ", ".join(mismatched_names)
            )

    else:

        results["issues"].append(
            "Insufficient name information for validation"
        )

    # --------------------------------------------------
    # 5. SURVEY NUMBER VALIDATION
    # --------------------------------------------------

    application_survey = (
        application.survey_number
    )

    extracted_survey = (
        land_data.get("survey_number")
    )

    if extracted_survey:

        if values_match(
            application_survey,
            extracted_survey
        ):

            results["survey_match"] = True

        else:

            results["issues"].append(
                "Survey number mismatch: "
                + str(application_survey)
                + " vs "
                + str(extracted_survey)
            )

    else:

        results["issues"].append(
            "Survey number not found in land record"
        )

    # --------------------------------------------------
    # 6. VILLAGE VALIDATION
    # --------------------------------------------------

    application_village = (
        application.village
    )

    extracted_village = (
        land_data.get("village")
    )

    if extracted_village:

        if values_match(
            application_village,
            extracted_village
        ):

            results["village_match"] = True

        else:

            results["issues"].append(
                "Village mismatch: "
                + str(application_village)
                + " vs "
                + str(extracted_village)
            )

    else:

        results["issues"].append(
            "Village not found in land record"
        )

    # --------------------------------------------------
    # 7. Document-level details
    # --------------------------------------------------

    for document in documents:

        extracted_data = get_extracted_data(
            document
        )

        results["document_details"].append({

            "document_type": document.document_type,

            "filename": document.filename,

            "ocr_confidence": (
                document.ocr_confidence
            ),

            "extracted_data": extracted_data
        })

    return results


def calculate_score(results):
    """
    Calculate transparent verification score.
    """

    score = 0

    # Document completeness = 25
    if results["documents_complete"]:
        score += 25

    # Name consistency = 30
    if results["name_match"]:
        score += 30

    # Survey consistency = 20
    if results["survey_match"]:
        score += 20

    # Village consistency = 15
    if results["village_match"]:
        score += 15

    # OCR quality = 10
    if results["ocr_quality"]:
        score += 10

    return score


def make_decision(score, results):
    """
    Determine whether the application can
    be processed automatically.
    """

    if (
        score >= 85
        and results["documents_complete"]
        and results["name_match"]
        and results["survey_match"]
        and results["village_match"]
        and results["ocr_quality"]
    ):

        return "AUTO_PROCESS"

    return "HUMAN_REVIEW"
