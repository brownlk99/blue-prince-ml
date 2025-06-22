import os
import random
from typing import Dict, List, Optional
import cv2
import easyocr
import numpy as np
from capture.ocr import easy_ocr, google_vision
from capture.resources import capture_resources
from capture.screen_capture import ScreenCapture
from capture.vision_utils import best_match, get_current_room
from google.cloud import vision
from loguru import logger

from capture.constants import ALPHANUMERIC_ALLOWLIST, REGIONS, ROOM_LIST, DIRECTORY, ROOM_LOOKUP
from door import Door
from house_map import HouseMap
from room import Room
from terminal import SecurityTerminal, LabTerminal, ShelterTerminal, OfficeTerminal


def capture_drafting_options(reader: easyocr.Reader, google_client: vision.ImageAnnotatorClient, current_room: Room, chosen_door: Door) -> List[Room]:
    drafting_options = []
    draft_regions = REGIONS["drafting"]                                         #regions for the left, center, and right drafts
    for draft, draft_region in draft_regions.items():
        draft_screenshot = ScreenCapture(draft_region).run()
        draft_screenshot = np.array(draft_screenshot)
        draft_screenshot = cv2.cvtColor(draft_screenshot, cv2.COLOR_RGB2BGR)

        draft_room_name = None
        if current_room.name == "DARKROOM":                 #edge case for dark room
            avg_brightness = np.mean(draft_screenshot)
            if avg_brightness < 15:                         #if dark room effect is active, we will not be able to read the draft.. if inactive, continue as normal
                draft_room_name = "UNKNOWN"
                cost = get_unknown_room_gem_requirement(draft)
                type = []
                description = "UNKNOWN"
                additional_info = "UNKNOWN"
                shape = "UNKNOWN"
                doors = None
                rarity = "UNKNOWN"
                terminal = "UNKNOWN"    #TODO: This might have to change
            else:
                draft_room_name = get_draft_room_name(reader, draft_screenshot, google_client)
        else:
            draft_room_name = get_draft_room_name(reader, draft_screenshot, google_client)

        if draft_room_name == "ARCHIVED FLOOR PLAN":
            cost = get_unknown_room_gem_requirement(draft)
            type = []
            description = "ARCHIVED FLOOR PLAN"
            additional_info = "ARCHIVED FLOOR PLAN"
            shape = "UNKNOWN"
            doors = None
            rarity = "UNKNOWN"
            terminal = "UNKNOWN"
        elif draft_room_name != "UNKNOWN":      # if we have a valid/possible room name
            print(f"Draft room name: {draft_room_name}")
            detected_doors = get_doors(draft_screenshot)                #get the detected doors from the draft screenshot
            valid = door_check(draft_room_name, len(detected_doors))          #make sure the number of doors matches the expected number for the room
            orientation = get_orientation(chosen_door, list(detected_doors))  #get the orientation of the doors based on the chosen door from the previous room and detected doors
            room = ROOM_LOOKUP[draft_room_name]                               #get the room data from the ROOM_LOOKUP dictionary
            cost = room["COST"]
            type = room["TYPE"]
            description = room["DESCRIPTION"]
            additional_info = room["ADDITIONAL INFORMATION"]
            shape = room["SHAPE"]
            doors = [Door(orientation=direction) for direction in orientation]
            rarity = room["RARITY"]
            if draft_room_name == "SECURITY":
                terminal = SecurityTerminal()
            elif draft_room_name == "LABORATORY":
                terminal = LabTerminal()
            elif draft_room_name == "SHELTER":
                terminal = ShelterTerminal()
            elif draft_room_name == "OFFICE":
                terminal = OfficeTerminal()
            else:
                terminal = None

        new_room = Room(
            name=draft_room_name,
            cost=cost,
            type=type,
            description=description,
            additional_info=additional_info,
            shape=shape,
            position=get_new_room_position(current_room.position, chosen_door.orientation),
            doors=doors,
            rarity=rarity,
            terminal=terminal
        )
        
        if draft_room_name not in ["ARCHIVED FLOOR PLAN", "UNKNOWN"] and not valid:
            new_room.edit_doors()  # if the door count is invalid, allow manual editing of doors

        new_room = HouseMap.specialize_room(new_room)  # TODO: change this to add any special characteristics to the room based on its type
        drafting_options.append(new_room)
    return drafting_options


def get_draft_room_name(reader: easyocr.Reader, img: np.ndarray, google_client: vision.ImageAnnotatorClient) -> str:
    top_half_of_draft = img[:img.shape[0] // 2, :, :]
    results = easy_ocr(reader, top_half_of_draft, True, ALPHANUMERIC_ALLOWLIST)
    for _, text in results:
        found_room_name = best_match(text, ROOM_LIST)
        if found_room_name:
            return found_room_name
    
    #for "ARCHIVED FLOOR PLAN"
    h = img.shape[0]
    middle_slice = img[int(h * 0.3):int(h * 0.7), :, :]
    middle_slice = cv2.cvtColor(middle_slice, cv2.COLOR_BGR2GRAY)
    results = google_vision(google_client, middle_slice)

    if "ARCHIVED" in results.strip().upper():
        return "ARCHIVED FLOOR PLAN"
    print("No room name found in draft.")
    return None


def door_check(room_name: str, actual_number: int) -> bool:
    """
        Checks if the actual number of doors in a room matches the expected number from the ROOM_LOOKUP directory.
            
            Args:
                room_name: The name of the room to check.
                actual_number: The actual number of doors detected (via OCR) in the room.
            Returns:
                True if the actual number matches the expected number, False otherwise.
    """
    characteristics = ROOM_LOOKUP.get(room_name)
    if not characteristics:
        logger.error(f"{room_name} not found in directory.")
        return False

    expected = characteristics.get("NUM_DOORS")
    if expected is None:
        logger.warning(f"{room_name}: No NUM_DOORS recorded in directory.")
        return False
    elif expected != actual_number:
        logger.warning(f"{room_name}: Expected {expected}, Got {actual_number}")
        return False
    else:
        print(f"{room_name}: Door count matches ({expected})")
    return True


def get_doors(img: np.ndarray, strip_length=8, offset=5, strip_height=8):
    """
    Detects which sides of a room have doors by sampling brightness at the center of each wall.

    Args:
        img: The room image as a NumPy array.
        strip_length: Width of the sampling strip along the wall.
        offset: Distance from the edge of the image to start sampling.
        strip_height: Height of the sampling strip.

    Returns:
        A set containing the directions ("top", "bottom", "left", "right") where doors are detected.
    """
    height, width, _ = img.shape

    # Calculate the center coordinates of the image
    mid_x, mid_y = width // 2, height // 2

    # Define sampling regions for each wall (top, bottom, left, right)
    regions = {
        "top": ((mid_x - strip_length//2, offset),
                (mid_x + strip_length//2, offset + strip_height)),
        "bottom": ((mid_x - strip_length//2, height - offset - strip_height),
                   (mid_x + strip_length//2, height - offset)),
        "left": ((offset, mid_y - strip_height//2),
                 (offset + strip_length, mid_y + strip_height//2)),
        "right": ((width - offset - strip_length, mid_y - strip_height//2),
                  (width - offset, mid_y + strip_height//2)),
    }

    detected_doors = set()  # Initialize an empty set to store detected doors within the draft image
    # For each wall, sample the region and check brightness
    for dir, (pt1, pt2) in regions.items():
        region_crop = img[pt1[1]:pt2[1], pt1[0]:pt2[0]]
        avg_brightness = np.mean(region_crop)
        # If the region is dark enough, assume a door is present
        if avg_brightness < 20:
            detected_doors.add(dir)

    return detected_doors

def get_orientation(chosen_door: Door, detected_doors: List[str]) -> List[str]:
    """
    Maps detected door positions on the image to cardinal directions,
    based on the direction the player entered the room.

    Args:
        chosen_door: The Door object representing the entry door, with an 'orientation' attribute ("N", "S", "E", "W").
        detected_doors: Iterable of strings ("top", "bottom", "left", "right") indicating where doors were detected on the image.

    Returns:
        A list of cardinal directions ("N", "S", "E", "W") corresponding to the detected doors, 
        adjusted for the entry orientation.
    """
    entry_orientation = chosen_door.orientation.upper()
    detected_doors = [d.upper() for d in detected_doors]

    orientation_map = {}

    # Set up the mapping from image sides to cardinal directions based on entry orientation
    if entry_orientation == "N":
        orientation_map = {
            "TOP": "N",
            "BOTTOM": "S",
            "LEFT": "W",
            "RIGHT": "E"
        }
    elif entry_orientation == "E":
        orientation_map = {
            "TOP": "E",
            "BOTTOM": "W",
            "LEFT": "N",
            "RIGHT": "S"
        }
    elif entry_orientation == "S":
        orientation_map = {
            "TOP": "S",
            "BOTTOM": "N",
            "LEFT": "E",
            "RIGHT": "W"
        }
    elif entry_orientation == "W":
        orientation_map = {
            "TOP": "W",
            "BOTTOM": "E",
            "LEFT": "S",
            "RIGHT": "N"
        }
    # Map each detected door position to its corresponding cardinal direction
    return [orientation_map[d] for d in detected_doors if d in orientation_map]

def get_new_room_position(current_position, direction):
    """
    Given a current (x, y) position and a cardinal direction,
    returns the new (x, y) position after moving one step.
    
    Direction must be one of: "N", "S", "E", "W"
    """
    x, y = current_position
    offsets = {
        "N": (0, -1),
        "S": (0, 1),
        "E": (1, 0),
        "W": (-1, 0)
    }

    if direction not in offsets:
        raise ValueError(f"Invalid direction '{direction}'. Must be one of {list(offsets.keys())}")

    dx, dy = offsets[direction]
    return (x + dx, y + dy)


def get_unknown_room_gem_requirement(draft: str):
    bbox = REGIONS["gem_requirement"][draft]
    gem_requirement_screenshot = ScreenCapture(bbox).run()
    gem_requirement_screenshot = np.array(gem_requirement_screenshot)

    template_folder = "./capture/gem_templates"
    template_paths = [
        os.path.join(template_folder, f)
        for f in os.listdir(template_folder)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    number_of_gems = count_gems(gem_requirement_screenshot, template_paths, threshold=0.8)
    user_input = input(f"Does the number of GEMS look correct for the {draft.upper()} draft? Y/n: ").strip().upper()
    if user_input == "N":
        while True:
            try:
                number_of_gems = int(input("Please enter the correct number of gems: "))
                if number_of_gems < 0:
                    raise ValueError("Number of gems cannot be negative.")
                break
            except ValueError as e:
                print(f"Invalid input: {e}. Please enter a valid number.")

    return number_of_gems

def count_gems(draft_img: np.ndarray, gem_template_paths: list[str], threshold: float = 0.8) -> int:
    draft_filtered = isolate_pink(draft_img)
    draft_gray = cv2.cvtColor(draft_filtered, cv2.COLOR_BGR2GRAY)

    total_matches = []
    for template_path in gem_template_paths:
        gem_template = cv2.imread(template_path)
        gem_filtered = isolate_pink(gem_template)
        gem_gray = cv2.cvtColor(gem_filtered, cv2.COLOR_BGR2GRAY)

        result = cv2.matchTemplate(draft_gray, gem_gray, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)

        w, h = gem_gray.shape[1], gem_gray.shape[0]
        for pt in zip(*locations[::-1]):
            total_matches.append([int(pt[0]), int(pt[1]), int(w), int(h)])

    # Group overlapping matches (non-max suppression)
    total_matches, _ = cv2.groupRectangles(total_matches, groupThreshold=1, eps=0.5)

    print(f"\nTotal GEM matches: {len(total_matches)}")
    return len(total_matches)

def isolate_pink(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_pink = np.array([140, 50, 50])
    upper_pink = np.array([170, 255, 255])
    mask = cv2.inRange(hsv, lower_pink, upper_pink)
    return cv2.bitwise_and(image, image, mask=mask)


def testing_make_random_room_choice(drafting_options: List[Room]) -> Room:
    """
    Selects a random Room from a list of drafting options.

    Args:
        drafting_options: A list of Room objects to choose from.

    Returns:
        A randomly chosen Room.
    """
    return random.choice(drafting_options)

def testing_make_random_door_choice():
    return random.choice(["W", "N", "E"])


if __name__ == "__main__":
    # Example usage
    reader = easyocr.Reader(['en'])
    google_client = vision.ImageAnnotatorClient()
    entrance_hall = Room(
            name="ENTRANCE HALL",
            shape="T",
            doors=[Door(locked=False, orientation="W"), Door(locked=False, orientation="N"), Door(locked=False, orientation="E")],
            description="",
            additional_info="",
            position=(2, 8)
        )
    darkroom = Room(
            name="DARKROOM",
            shape="CROSS",
            doors=[Door(locked=False, orientation="W"), Door(locked=False, orientation="N"), Door(locked=False, orientation="S"), Door(locked=False, orientation="E")],
            description="",
            additional_info="",
            position=(2, 7)
        )
    chosen_door = darkroom.doors[0]  # Example chosen door
    drafting_options = capture_drafting_options(reader, google_client, darkroom, chosen_door)