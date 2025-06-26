import hashlib
import time
import cv2
import numpy as np
from google.cloud import vision
from capture.ocr import google_vision
from capture.screen_capture import ScreenCapture
from datetime import datetime
import os

from capture.constants import NUMERIC_ALLOWLIST, REGIONS

last_resource_hashes = {}

def image_hash(img):
    return hashlib.md5(img.tobytes()).hexdigest()

def trim_template(template_img: np.ndarray) -> np.ndarray:
    """Trim whitespace/background from template image."""
    # Convert to grayscale if needed
    if len(template_img.shape) == 3:
        gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = template_img
    
    # Find non-zero pixels (the actual number)
    coords = cv2.findNonZero(gray)
    if coords is None:
        return template_img
    
    # Get bounding rectangle
    x, y, w, h = cv2.boundingRect(coords)
    
    # Crop to just the number
    return template_img[y:y+h, x:x+w]

def recognize_number(resource_img: np.ndarray, number_template_paths: list[str], threshold: float = 0.8) -> int:
    """Recognize the actual number in resource image using template matching."""
    # Check if image is already grayscale (single channel)
    if len(resource_img.shape) == 3:
        resource_gray = cv2.cvtColor(resource_img, cv2.COLOR_BGR2GRAY)
    else:
        resource_gray = resource_img
    
    # Sort templates by length (longest first) to prioritize multi-digit numbers
    template_paths_sorted = sorted(number_template_paths, 
                                  key=lambda x: len(os.path.basename(x).split('.')[0]), 
                                  reverse=True)
    
    best_match = None
    best_score = 0
    
    for template_path in template_paths_sorted:
        number_template = cv2.imread(template_path)
        if number_template is None:
            continue
            
        # Get the number from filename (e.g., "44.png" -> "44")
        template_name = os.path.basename(template_path).split('.')[0]
        try:
            template_number = int(template_name)
        except ValueError:
            continue  # Skip if filename isn't a number
            
        # Trim the template to just the number
        number_template = trim_template(number_template)
        
        # Convert to grayscale if it's not already
        if len(number_template.shape) == 3:
            number_gray = cv2.cvtColor(number_template, cv2.COLOR_BGR2GRAY)
        else:
            number_gray = number_template
        
        result = cv2.matchTemplate(resource_gray, number_gray, cv2.TM_CCOEFF_NORMED)
        max_score = np.max(result)
        
        if max_score > threshold and max_score > best_score:
            best_score = max_score
            best_match = template_number
    
    return best_match if best_match is not None else 0

def save_and_rename_template(resource_screenshot: np.ndarray, resource: str, template_folder: str, prefix: str = "unknown") -> int:
    """Save a template image and prompt user to rename it with the correct number. Returns the user-entered value."""
    
    # Ask user to rename the file with the correct number
    while True:
        user_number = input(f"\nWhat is the current value of {resource} (or press Enter to skip): ").strip()

        if user_number and user_number.isdigit():
            # Check if target file already exists
            filepath = os.path.join(template_folder, f"{user_number}.png")
            if not os.path.exists(filepath):
                cv2.imwrite(filepath, resource_screenshot)
                print(f"\nSaved template to {filepath}")
            return int(user_number)
        elif user_number == "":
            return 0  # Return 0 if user skips
        else:
            print("\nInvalid input. Please enter a valid number.")
            time.sleep(3)

def capture_resources(client: vision.ImageAnnotatorClient, current_game_state_resources: dict) -> dict:
    available_resources = {}
    template_folder = "./capture/number_templates"
    
    # Get all number template paths
    number_template_paths = [
        os.path.join(template_folder, f)
        for f in os.listdir(template_folder)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    
    for resource, bbox in REGIONS["resources"].items():
        resource_screenshot = ScreenCapture(bbox).run()
        resource_screenshot = np.array(resource_screenshot)
        resource_screenshot = cv2.cvtColor(resource_screenshot, cv2.COLOR_BGR2GRAY)
        resource_screenshot = cv2.resize(resource_screenshot, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
        _, resource_screenshot = cv2.threshold(resource_screenshot, 205, 255, cv2.THRESH_BINARY_INV)

        # Check if image is completely white (no content detected)
        if np.mean(resource_screenshot) > 253:  # Threshold for "mostly white"
            print(f"Resource {resource}: No content detected, setting to 0")
            available_resources[resource] = 0
            continue

        img_hash = image_hash(resource_screenshot)
        if last_resource_hashes.get(resource) == img_hash:
            print(f"Resource {resource} unchanged, using cached value.")
            if resource in current_game_state_resources:
                available_resources[resource] = current_game_state_resources[resource]
            continue

        result = google_vision(client, resource_screenshot)
        last_resource_hashes[resource] = img_hash

        if result == "":
            # Try template matching as fallback
            value = recognize_number(resource_screenshot, number_template_paths)
            print(f"Resource {resource}: OCR failed, template matching found: {value}")
            
            # Save template and ask user what number it is
            if value == 0:
                value = save_and_rename_template(resource_screenshot, resource, template_folder, "unknown")
        else:       #gets words back from OCR
            try:
                value = int(result)
            except ValueError:
                # Try template matching as fallback
                value = recognize_number(resource_screenshot, number_template_paths)
                print(f"Resource {resource}: OCR conversion failed, template matching found: {value}")
                
                # Save template and ask user what number it is
                if value == 0:
                    value = save_and_rename_template(resource_screenshot, resource, template_folder, "failed_convert")

        available_resources[resource] = value
    
    return available_resources