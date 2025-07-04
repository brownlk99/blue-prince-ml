import cv2
import easyocr
import numpy as np
from google.cloud import vision
from typing import List, Tuple, Union


def easy_ocr(reader: easyocr.Reader, img: np.ndarray, paragraph: bool, allowlist: str) -> List:
    """
        Perform OCR on an image using EasyOCR

            Args:
                reader (easyocr.Reader): Initialized EasyOCR reader instance
                img (np.ndarray): Input image as numpy array
                paragraph (bool): Whether to treat text as paragraphs
                allowlist (str): String of allowed characters for recognition

            Returns:
                List: List of OCR results containing bounding box coordinates, detected text, and confidence scores
    """
    results = reader.readtext(img, detail=1, paragraph=paragraph, allowlist=allowlist)
    return results

def google_vision(client: vision.ImageAnnotatorClient, img: np.ndarray) -> str:
    """
        Perform OCR on an image using Google Vision API

            Args:
                client (vision.ImageAnnotatorClient): Google Vision API client
                img (np.ndarray): Input image as numpy array

            Returns:
                str: Detected text from the image, or empty string if no text found
    """
    success, encoded_image = cv2.imencode('.jpg', img)
    if not success:
        raise Exception("Failed to encode image")

    content = encoded_image.tobytes()
    image = vision.Image(content=content)

    response = client.text_detection(image=image)  # type: ignore
    texts = response.text_annotations

    if texts:
        return texts[0].description
    else:
        print("No text detected.")
        return ""