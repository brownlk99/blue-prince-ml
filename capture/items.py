import time
from typing import Dict, Optional, Union

import cv2
import numpy as np
from google.cloud import vision

from capture.ocr import google_vision
from capture.screen_capture import ScreenCapture
from capture.vision_utils import best_match
from game.constants import DIRECTORY

def capture_items(client: vision.ImageAnnotatorClient) -> Optional[Union[str, dict]]:
    """
        Capture item information either through screenshot or manual entry

            Args:
                client: Google Vision API client for OCR

            Returns:
                Item details dictionary, cancellation message string, or None if failed
    """
    print("1. Capture with screenshot")
    print("2. Enter manually")
    
    capture_choice = input("Enter your choice (1/2): ").strip()
    
    if capture_choice == "1":
        # Screenshot capture path
        item_screenshot = ScreenCapture().run()
        if item_screenshot is None:
            return "Screenshot capture was cancelled."
        else:
            item_screenshot = np.array(item_screenshot)
            item_screenshot = cv2.cvtColor(item_screenshot, cv2.COLOR_RGB2BGR)
            result = google_vision(client, item_screenshot)
            item = best_match(result.upper().strip(), DIRECTORY["ITEMS"].keys())
            item_details = DIRECTORY["ITEMS"].get(item, None)
            if item_details is None:
                print(f"Item '{item}' not recognized or not in directory.")
                return None
            else:
                return {item: item_details}
    elif capture_choice == "2":
        # Manual entry path
        return manually_obtain_item()
    else:
        print("\nInvalid choice. Please enter 1 or 2.")
        time.sleep(2)
        return None


def manually_obtain_item() -> Optional[dict]:
    """
        Manually enter item information by selecting from available items

            Returns:
                Item details dictionary or None if cancelled
    """
    item_dict = DIRECTORY.get("ITEMS", {})
    print("Available items:")
    for item in item_dict.keys():
        print(f"- {item}")
    print("\nPress \"q\" to cancel")
    item_name = input("\nEnter the name of the item you want to add: ").strip().upper()
    while True:
        item_details = item_dict.get(item_name, None)
        if item_name == 'Q':
            print("Item capture cancelled.")
            return None
        elif item_details is None:
            print(f"\nItem '{item_name}' not recognized or not in directory.")
            time.sleep(2)
            item_name = input("\nPlease re-enter a valid item name: ").strip().upper()
        else:
            return {item_name: item_details}