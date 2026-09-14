import os
import cv2
import fitz
import pytesseract
import numpy as np

from PIL import Image
from pytesseract import Output


def preprocess_image(image):
    """
    Convert image to grayscale and apply
    thresholding to improve OCR quality.
    """

    image_array = np.array(image)

    gray = cv2.cvtColor(
        image_array,
        cv2.COLOR_RGB2GRAY
    )

    gray = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    return Image.fromarray(gray)


def ocr_image(image):
    """
    Run OCR and calculate an actual confidence
    score from Tesseract.
    """

    processed = preprocess_image(image)

    # Extract text
    text = pytesseract.image_to_string(
        processed
    )

    # Extract word-level confidence values
    data = pytesseract.image_to_data(
        processed,
        output_type=Output.DICT
    )

    confidence_values = []

    for confidence in data["conf"]:

        try:

            value = float(confidence)

            if value >= 0:
                confidence_values.append(value)

        except (ValueError, TypeError):
            continue

    if confidence_values:

        confidence = (
            sum(confidence_values)
            / len(confidence_values)
        )

        confidence = confidence / 100.0

    else:

        confidence = 0.0

    return text, confidence


def ocr_pdf(filepath):
    """
    Convert each PDF page into an image,
    run OCR and calculate the average
    confidence across pages.
    """

    document = fitz.open(filepath)

    all_text = []
    all_confidences = []

    for page in document:

        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(2, 2)
        )

        image = Image.frombytes(
            "RGB",
            [pixmap.width, pixmap.height],
            pixmap.samples
        )

        text, confidence = ocr_image(
            image
        )

        all_text.append(text)
        all_confidences.append(
            confidence
        )

    document.close()

    if all_confidences:

        average_confidence = (
            sum(all_confidences)
            / len(all_confidences)
        )

    else:

        average_confidence = 0.0

    return (
        "\n".join(all_text),
        average_confidence
    )


def extract_text(filepath):
    """
    OCR a PDF or image.

    Returns:
        text
        confidence
    """

    extension = (
        os.path.splitext(filepath)[1]
        .lower()
    )

    if extension == ".pdf":

        return ocr_pdf(
            filepath
        )

    if extension in [
        ".png",
        ".jpg",
        ".jpeg"
    ]:

        image = Image.open(
            filepath
        )

        return ocr_image(
            image
        )

    raise ValueError(
        "Unsupported file format"
    )
