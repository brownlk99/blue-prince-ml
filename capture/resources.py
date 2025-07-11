import hashlib
import os
import time
from typing import Optional

import cv2
import numpy as np
from google.cloud import vision

from capture.constants import REGIONS
from capture.ocr import google_vision
from capture.screen_capture import ScreenCapture
from utils import get_color_code


last_resource_hashes = {}

def image_hash(img: np.ndarray) -> str:
    """
        Calculate MD5 hash of an image

            Args:
                img: Input image as numpy array

            Returns:
                MD5 hash of the image as hexadecimal string
    """
    return hashlib.md5(img.tobytes()).hexdigest()


def trim_template(template_img: np.ndarray) -> np.ndarray:
    """
        Trim whitespace/background from template image

            Args:
                template_img: The template image to trim

            Returns:
                The trimmed template image
    """
    # convert to grayscale if needed
    if len(template_img.shape) == 3:
        gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = template_img
    
    # find non-zero pixels (the actual number)
    coords = cv2.findNonZero(gray)
    if coords is None:
        return template_img
    
    # get bounding rectangle
    x, y, w, h = cv2.boundingRect(coords)
    
    # crop to just the number
    return template_img[y:y+h, x:x+w]


def recognize_number(resource_img: np.ndarray, number_template_paths: list[str], threshold: float = 0.75) -> Optional[int]:
    """
        Recognize the actual number in resource image using template matching

            Args:
                resource_img: The resource image containing the number
                number_template_paths: List of paths to number template images
                threshold: Matching threshold for template matching

            Returns:
                The recognized number, or None if no match found
    """
    # check if image is already grayscale (single channel)
    if len(resource_img.shape) == 3:
        resource_gray = cv2.cvtColor(resource_img, cv2.COLOR_BGR2GRAY)
    else:
        resource_gray = resource_img
    
    # sort templates by length (longest first) to prioritize multi-digit numbers
    template_paths_sorted = sorted(
        number_template_paths,
        key=lambda x: len(os.path.basename(x).split('_')[0]),
        reverse=True
    )
    
    best_match = None
    best_score = 0
    
    for template_path in template_paths_sorted:
        number_template = cv2.imread(template_path)
        if number_template is None:
            continue
            
        # get the number from filename (e.g., "44_1.png" -> "44")
        template_name = os.path.basename(template_path).split('_')[0]
        try:
            template_number = int(template_name)
        except ValueError:
            continue  # skip if filename isn't a number
            
        # trim the template to just the number
        number_template = trim_template(number_template)
        
        # convert to grayscale if it's not already
        if len(number_template.shape) == 3:
            number_gray = cv2.cvtColor(number_template, cv2.COLOR_BGR2GRAY)
        else:
            number_gray = number_template
        
        result = cv2.matchTemplate(resource_gray, number_gray, cv2.TM_CCOEFF_NORMED)
        max_score = np.max(result)
        
        if max_score > threshold and max_score > best_score:
            best_score = max_score
            best_match = template_number
    
    return best_match  # returns None if no match found


def save_and_rename_template(resource_screenshot: np.ndarray, resource: str, template_folder: str, prefix: str = "unknown") -> int:
    """
        Save a resource screenshot as a new template and prompt user for the number value

            Args:
                resource_screenshot: Screenshot of the resource as numpy array
                resource: Name of the resource being captured
                template_folder: Path to folder where templates are stored
                prefix: Prefix for the filename if needed

            Returns:
                The number value provided by the user
    """
    while True:
        user_number = input(f"\nWhat is the current value of {get_color_code(resource)} (or press Enter to skip): ").strip()
        if user_number and user_number.isdigit():
            base = user_number
            # find all files that start with the digit and underscore
            existing = [f for f in os.listdir(template_folder) if f.startswith(f"{base}_") and f.endswith('.png')]
            indices = []
            for f in existing:
                parts = f.replace('.png', '').split('_')
                if len(parts) == 2 and parts[1].isdigit():
                    indices.append(int(parts[1]))
            next_index = max(indices) + 1 if indices else 1
            filename = f"{base}_{next_index}.png"
            filepath = os.path.join(template_folder, filename)
            cv2.imwrite(filepath, resource_screenshot)
            print(f"\nSaved template to {filepath}")
            return int(user_number)
        elif user_number == "":
            return 0  # Return 0 if user skips
        else:
            print("\nInvalid input. Please enter a valid number.")
            time.sleep(2)


def capture_resources(client: vision.ImageAnnotatorClient, current_game_state_resources: dict) -> dict:
    """
        Capture current resource values from the screen using OCR and template matching

            Args:
                client: Google Vision API client for OCR
                current_game_state_resources: Current game state resources for caching

            Returns:
                Dictionary containing current resource values
    """
    available_resources = {}
    template_folder = "./capture/number_templates"
    
    # get all number template paths
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

        # check if image is completely white (no content detected)
        if np.mean(resource_screenshot) > 253:  # threshold for "mostly white"
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
            # try template matching as fallback
            value = recognize_number(resource_screenshot, number_template_paths)
            print(f"\nResource {resource}: OCR failed, template {value} was matched")
            
            # save template and ask user what number it is
            if value is None:
                value = save_and_rename_template(resource_screenshot, resource, template_folder, "unknown")
        else:  # gets words back from OCR
            try:
                value = int(result)
            except ValueError:
                # try template matching as fallback
                value = recognize_number(resource_screenshot, number_template_paths)
                print(f"\nResource {resource}: OCR conversion failed, template {value} was matched")
                
                # save template and ask user what number it is
                if value is None:
                    value = save_and_rename_template(resource_screenshot, resource, template_folder, "failed_convert")

        available_resources[resource] = value
    
    return available_resources