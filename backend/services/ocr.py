import os
import re

import cv2
import fitz
import pytesseract
import numpy as np
from PIL import Image


def preprocess_image(image):
    """
    Convert image to grayscale and improve OCR readability.
    """

    image_array = np.array(image)

    gray = cv2.cvtColor(
        image_array,
        cv2.COLOR_RGB2GRAY
    )

    # Improve contrast
    gray = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    return Image.fromarray(gray)


def ocr_image(image):
    """
    Run Tesseract OCR on an image.
    """

    processed = preprocess_image(image)

    text = pytesseract.image_to_string(
        processed
    )

    return text


def ocr_pdf(filepath):
    """
    Convert PDF pages to images and run OCR.
    """

    document = fitz.open(filepath)

    all_text = []

    for page in document:

        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(2, 2)
        )

        image = Image.frombytes(
            "RGB",
            [
                pixmap.width,
                pixmap.height
            ],
            pixmap.samples
        )

        text = ocr_image(image)

        all_text.append(text)

    document.close()

    return "\n".join(all_text)


def extract_text(filepath):
    """
    Run OCR depending on file type.
    """

    extension = os.path.splitext(
        filepath
    )[1].lower()

    if extension == ".pdf":
        return ocr_pdf(filepath)

    if extension in [
        ".png",
        ".jpg",
        ".jpeg"
    ]:

        image = Image.open(filepath)

        return ocr_image(image)

    raise ValueError(
        "Unsupported file format"
    )
