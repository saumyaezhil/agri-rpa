import re


def clean_text(text):
    return " ".join(
        text.split()
    )


def extract_name(text):
    """
    Attempt to extract a name from OCR text.
    """

    patterns = [
        r"(?:Name|Applicant Name|Farmer Name)\s*[:\-]\s*([A-Za-z ]+)",
        r"(?:Name of Owner|Owner Name)\s*[:\-]\s*([A-Za-z ]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(1).strip()

    return None


def extract_survey_number(text):
    """
    Extract survey number.
    """

    patterns = [
        r"(?:Survey Number|Survey No|Survey)\s*[:\-]?\s*([A-Za-z0-9\/\-]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(1).strip()

    return None


def extract_village(text):
    """
    Extract village name.
    """

    patterns = [
        r"(?:Village|Village Name)\s*[:\-]\s*([A-Za-z ]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(1).strip()

    return None


def extract_fields(text, document_type):

    data = {
        "name": extract_name(text),
        "survey_number": extract_survey_number(text),
        "village": extract_village(text)
    }

    # Identity documents may not contain
    # survey/village information.
    if document_type == "identity_proof":

        data.pop(
            "survey_number",
            None
        )

    return data

