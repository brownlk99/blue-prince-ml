import easyocr
from room import Room, ShopRoom
from capture.constants import REGIONS, DIRECTORY, ALPHANUMERIC_ALLOWLIST
from capture.screen_capture import ScreenCapture
import cv2
import numpy as np
from capture.ocr import easy_ocr
from capture.vision_utils import best_match


def stock_shelves(reader: easyocr.Reader, current_room: ShopRoom):
    """
        Capture items in stock within the current shop room

            Args:
                reader (easyocr.Reader): Initialized EasyOCR reader for text recognition
                current_room (Room): The current room object representing the shop
    """
    if "SHOP" in current_room.type:
        items = {}
        if current_room.name == "COMMISSARY":
            for item, region in REGIONS["commissary"].items():
                item_screenshot = ScreenCapture(region).run()
                item_screenshot = np.array(item_screenshot)
                item_screenshot = cv2.cvtColor(item_screenshot, cv2.COLOR_RGB2BGR)
                results = easy_ocr(reader, item_screenshot, paragraph=False, allowlist=ALPHANUMERIC_ALLOWLIST)
                for _, text, confidence in results:
                    print(f"Detected text: {text} with confidence {confidence}")
                    item = best_match(text.upper(), DIRECTORY["FLOORPLANS"]["SHOPS"]["COMMISSARY"]["POTENTIAL_ITEMS"].keys())
                    if item:
                        price = DIRECTORY["FLOORPLANS"]["SHOPS"]["COMMISSARY"]["POTENTIAL_ITEMS"].get(item)
                        items[item] = price
        elif current_room.name == "KITCHEN":
            for item, region in REGIONS["kitchen"].items():
                item_screenshot = ScreenCapture(region).run()
                item_screenshot = np.array(item_screenshot)
                item_screenshot = cv2.cvtColor(item_screenshot, cv2.COLOR_RGB2BGR)
                results = easy_ocr(reader, item_screenshot, paragraph=False, allowlist=ALPHANUMERIC_ALLOWLIST)
                for _, text, confidence in results:
                    item = best_match(text.upper(), DIRECTORY["FLOORPLANS"]["SHOPS"]["KITCHEN"]["POTENTIAL_ITEMS"].keys())
                    if item:
                        price = DIRECTORY["FLOORPLANS"]["SHOPS"]["KITCHEN"]["POTENTIAL_ITEMS"].get(item)
                        items[item] = price
        elif current_room.name == "SHOWROOM":
            print("NOT IMPLEMENTED YET")
        elif current_room.name == "LOCKSMITH":
            items = DIRECTORY["FLOORPLANS"]["SHOPS"]["LOCKSMITH"]["POTENTIAL_ITEMS"]

        current_room.items_for_sale = items
    else:
        print("Current room is not a shop. No items to stock.")