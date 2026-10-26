
import os
import pytesseract
import fitz
import cv2
import numpy as np

from PIL import Image
from pytesseract import Output


# Windows Tesseract installation path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def _ocr_image(image):
    """
    Run OCR on an image and return extracted text and confidence.
    """
    if image is None:
        return "", 0.0

    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Improve readability before OCR
    processed = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )[1]

    data = pytesseract.image_to_data(
        processed,
        output_type=Output.DICT,
        config="--oem 3 --psm 6",
    )

    words = []
    confidences = []

    for word, confidence in zip(data["text"], data["conf"]):
        word = word.strip()

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            continue

        if word and confidence >= 0:
            words.append(word)
            confidences.append(confidence)

    text = " ".join(words)

    average_confidence = (
        sum(confidences) / len(confidences) / 100.0
        if confidences
        else 0.0
    )

    return text, round(average_confidence, 4)


def extract_text(filepath):
    """
    Extract text from a PDF or image file.

    Returns:
        tuple: (extracted_text, confidence)
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(
            f"Document not found: {filepath}"
        )

    extension = os.path.splitext(filepath)[1].lower()

    # Extract text directly from PDFs first.
    if extension == ".pdf":
        document = fitz.open(filepath)

        try:
            page_texts = []
            page_confidences = []

            for page in document:
                text = page.get_text().strip()

                # Scanned PDFs may not contain an embedded text layer.
                if text:
                    page_texts.append(text)
                    page_confidences.append(1.0)
                else:
                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(2, 2),
                        alpha=False,
                    )

                    image = np.frombuffer(
                        pix.samples,
                        dtype=np.uint8,
                    ).reshape(
                        pix.height,
                        pix.width,
                        pix.n,
                    )

                    if pix.n == 4:
                        image = cv2.cvtColor(
                            image,
                            cv2.COLOR_RGBA2BGR,
                        )
                    else:
                        image = cv2.cvtColor(
                            image,
                            cv2.COLOR_RGB2BGR,
                        )

                    ocr_text, confidence = _ocr_image(image)

                    if ocr_text:
                        page_texts.append(ocr_text)

                    page_confidences.append(confidence)

            extracted_text = "\n".join(page_texts).strip()

            confidence = (
                sum(page_confidences) / len(page_confidences)
                if page_confidences
                else 0.0
            )

            return extracted_text, round(confidence, 4)

        finally:
            document.close()

    # Handle common image formats.
    elif extension in (
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".tif",
        ".tiff",
    ):
        image = cv2.imread(filepath)

        if image is None:
            raise ValueError(
                f"Could not read image: {filepath}"
            )

        return _ocr_image(image)

    else:
        raise ValueError(
            f"Unsupported document format: {extension}"
        )
