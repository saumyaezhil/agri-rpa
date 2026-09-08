def classify_document(text, filename):
    """
    Prototype document classifier.

    Uses OCR keywords and filename hints.
    This can later be replaced by an ML model.
    """

    text_lower = text.lower()
    filename_lower = filename.lower()

    # Identity proof
    if (
        "aadhaar" in text_lower
        or "aadhaar" in filename_lower
        or "identity" in filename_lower
    ):
        return "identity_proof"

    # Land record
    if (
        "survey number" in text_lower
        or "land record" in text_lower
        or "patta" in text_lower
        or "land" in filename_lower
    ):
        return "land_record"

    # Address
    if (
        "address proof" in text_lower
        or "address" in filename_lower
        or "residential" in text_lower
    ):
        return "address_proof"

    return "unknown"
