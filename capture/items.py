import cv2
import numpy as np
from capture.screen_capture import ScreenCapture
from capture.ocr import google_vision
from google.cloud import vision
from capture.vision_utils import best_match

from capture.constants import DIRECTORY


def capture_items(client: vision.ImageAnnotatorClient):
    item_dict = {}
    item_screenshot = ScreenCapture().run()
    item_screenshot = np.array(item_screenshot)
    item_screenshot = cv2.cvtColor(item_screenshot, cv2.COLOR_RGB2BGR)
    result = google_vision(client, item_screenshot)
    item = best_match (result.upper(), DIRECTORY["ITEMS"].keys())
    item_details = DIRECTORY["ITEMS"].get(item, None)
    if item_details is None:
        print(f"Item '{item}' not recognized or not in directory.")
    else:
        item_dict[item] = item_details
        return item_dict