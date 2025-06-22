import cv2
import numpy as np
from capture.screen_capture import ScreenCapture
from capture.ocr import google_vision
from google.cloud import vision
from capture.vision_utils import best_match

from capture.constants import DIRECTORY


def capture_items(client: vision.ImageAnnotatorClient):
    item_screenshot = ScreenCapture().run()
    if item_screenshot is None:
        return "Screenshot capture was cancelled."        #TODO: change this... it's so gross
    else:
        item_screenshot = np.array(item_screenshot)
        item_screenshot = cv2.cvtColor(item_screenshot, cv2.COLOR_RGB2BGR)
        result = google_vision(client, item_screenshot)
        item = best_match (result.upper().strip(), DIRECTORY["ITEMS"].keys())
        item_details = DIRECTORY["ITEMS"].get(item, None)
        if item_details is None:
            print(f"Item '{item}' not recognized or not in directory.")
            return None
        else:
            return {item:item_details}

def manually_obtain_item():
    item_dict = DIRECTORY.get("ITEMS", {})
    print("Available items:")
    for item in item_dict.keys():
        print(f"- {item}")
    print("Press q to cancel")
    item_name = input("\nEnter the name of the item you want to add: ").strip().upper()
    while True:
        item_details = item_dict.get(item_name, None)
        if item_name == 'Q':
            print("Item capture cancelled.")
            return None
        elif item_details is None:
            print(f"Item '{item_name}' not recognized or not in directory.")
            item_name = input("\nPlease re-enter a valid item name: ").strip().upper()
        else:
            return item_name, item_details