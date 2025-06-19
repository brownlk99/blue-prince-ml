import difflib
import os
import subprocess
import tempfile
import time
import cv2
from loguru import logger
import numpy as np
from textblob import TextBlob

from capture.constants import ALPHANUMERIC_ALLOWLIST, REGIONS, ROOM_LOOKUP
from capture.ocr import easy_ocr
from capture.screen_capture import ScreenCapture
from room import Room


def best_match(text, options):
    match = difflib.get_close_matches(text.upper(), options, n=1, cutoff=0.6)
    if len(match) > 1:
        print("MATCH GREATER THAN 1 CHOOSE")
        #TODO: add in an option to choose..
        return None
    if match:
        return match[0]
    else:
        print(f"No close match found for '{text}' in options.")
        return None
    
def generic_autocorrect(text):
    blob = TextBlob(text)
    corrected = blob.correct()
    return str(corrected)

def edit_text_in_editor(text: str) -> str:
    logger.info("Editing text in external editor, save and close to continue.")
    editor_path = os.environ.get("EDITOR_PATH")
    if not editor_path:
        raise EnvironmentError("EDITOR_PATH environment variable not set.")            
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode='w+', encoding='utf-8') as tf:
        tf.write(text)
        tf.flush()
        subprocess.call([editor_path, "--wait", tf.name])
        tf.seek(0)                              # go back to top of file
        edited = tf.read()                      # read the edited content
    os.remove(tf.name)
    return edited.strip()

def get_current_room(reader, house) -> Room:
    if house.count_occupied_rooms() == 2:                           #default set up (no current room displayed when in Entrance Hall on a new run)
        current_room_obj = house.get_room_by_name("ENTRANCE HALL")
        return current_room_obj
    else:
        current_room_name = get_current_room_name(reader)
        current_room_obj = None
        current_room_obj = house.get_room_by_name(current_room_name)
        if current_room_obj:
            return current_room_obj
        else:
            print(f"Current room '{current_room_name}' not found in house map. Prompting user for manual input.")
            current_room_obj = house.prompt_for_room_name(current_room_name)
            return current_room_obj

def get_current_room_name(reader) -> str:
    bbox = REGIONS["other"]["current_room"]
    current_room_screenshot = ScreenCapture(bbox).run()
    current_room_screenshot = np.array(current_room_screenshot)
    current_room_screenshot = cv2.cvtColor(current_room_screenshot, cv2.COLOR_RGB2BGR)
    results = easy_ocr(reader, current_room_screenshot, False, ALPHANUMERIC_ALLOWLIST)
    for _, text, _ in results:
        current_room = best_match(text, list(ROOM_LOOKUP.keys()))
        if current_room:
            return current_room
    print("No room detected by OCR. Prompting user for manual input.")
    time.sleep(1) 
    while True:
        room_name = input("\nPlease enter the room name: ").strip().upper()
        if room_name in ROOM_LOOKUP:
            return room_name
        print("Invalid room name. Please try again.")
        time.sleep(1)
