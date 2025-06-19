import hashlib
import cv2
import numpy as np
from google.cloud import vision
from capture.ocr import google_vision
from capture.screen_capture import ScreenCapture

from capture.constants import NUMERIC_ALLOWLIST, REGIONS

last_resource_hashes = {}
last_resource_values = {}

def image_hash(img):
    return hashlib.md5(img.tobytes()).hexdigest()

def capture_resources(client: vision.ImageAnnotatorClient) -> dict:
    available_resources = {}
    for resource, bbox in REGIONS["resources"].items():
        resource_screenshot = ScreenCapture(bbox).run()
        resource_screenshot = np.array(resource_screenshot)
        resource_screenshot = cv2.cvtColor(resource_screenshot, cv2.COLOR_RGB2BGR)
        resource_screenshot = cv2.resize(resource_screenshot, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
        _, resource_screenshot = cv2.threshold(resource_screenshot, 195, 255, cv2.THRESH_BINARY_INV)

        img_hash = image_hash(resource_screenshot)
        if last_resource_hashes.get(resource) == img_hash:
            # No change, return last known value if available
            print(f"Resource {resource} unchanged, using cached value.")
            if resource in last_resource_values:
                available_resources[resource] = last_resource_values[resource]
            continue

        result = google_vision(client, resource_screenshot)
        last_resource_hashes[resource] = img_hash
        if result == "":
            # Keep the resource value the same as before if result is empty
            value = last_resource_values.get(resource, 0)
        else:
            value = int(result)
        last_resource_values[resource] = value
        available_resources[resource] = value
    return available_resources