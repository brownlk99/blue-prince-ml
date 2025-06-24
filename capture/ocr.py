import cv2
from google.cloud import vision
import numpy as np


def easy_ocr(reader, img, paragraph, allowlist):
    results = reader.readtext(img, detail=1, paragraph=paragraph, allowlist=allowlist)
    return results

def google_vision(client: vision.ImageAnnotatorClient, img: np.ndarray) -> str:
    success, encoded_image = cv2.imencode('.jpg', img)
    if not success:
        raise Exception("Failed to encode image")

    content = encoded_image.tobytes()
    image = vision.Image(content=content)

    response = client.text_detection(image=image)   # type: ignore
    texts = response.text_annotations

    if texts:
        return texts[0].description
    else:
        print("No text detected.")
        return ""