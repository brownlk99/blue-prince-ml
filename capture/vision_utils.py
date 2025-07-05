import difflib
import os
import subprocess
import tempfile
import time
from typing import Optional, Union, Iterable
import cv2
import easyocr
import numpy as np
from textblob import TextBlob

from capture.constants import ALPHANUMERIC_ALLOWLIST, REGIONS
from capture.ocr import easy_ocr
from capture.screen_capture import ScreenCapture
from game.constants import ROOM_LOOKUP


def best_match(text: str, options: Iterable[str]) -> Optional[str]:
    """
        Find the best matching option for the given text using fuzzy matching

            Args:
                text: Input text to match against options
                options: Collection of valid options to match against

            Returns:
                Best matching option or None if no good match found
    """
    match = difflib.get_close_matches(text.upper(), options, n=1, cutoff=0.6)
    if len(match) > 1:
        print("MATCH GREATER THAN 1 CHOOSE")
        # TODO: add in an option to choose
        return None
    if match:
        return match[0]
    else:
        print(f"\nNo close match found for '{text}' in AVAILABLE OPTIONS.")
        return None
    
def generic_autocorrect(text: str) -> str:
    """
        Apply autocorrection to text using TextBlob

            Args:
                text: Input text to autocorrect

            Returns:
                Autocorrected text
    """
    blob = TextBlob(text)
    corrected = blob.correct()
    return str(corrected)

def edit_text_in_editor(text: str, editor_path: Optional[str] = None) -> str:
    print("Editing text in external editor, save and close to continue.")
    
    # Priority: 1. Function argument, 2. Environment variable, 3. Default
    if editor_path is None:
        editor_path = os.environ.get("EDITOR_PATH")
    
    if not editor_path:
        # Platform-specific defaults
        if os.name == 'nt':  # Windows
            editor_path = "notepad"
        else:  # Unix/Linux/Mac
            editor_path = "nano"
    
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode='w+', encoding='utf-8') as tf:
        tf.write(text)
        tf.flush()
        subprocess.call([editor_path, "--wait", tf.name])
        tf.seek(0)  # go back to top of file
        edited = tf.read()  # read the edited content
    os.remove(tf.name)
    return edited.strip()

def get_current_room(reader: easyocr.Reader, house) -> Union[None, object]:
    """
        Get the current room object based on OCR detection or house state

            Args:
                reader: Initialized EasyOCR reader for text recognition
                house: House map object containing room information

            Returns:
                Current room object or None if not found
    """
    if house.count_occupied_rooms() == 2:  # default set up (no current room displayed when in Entrance Hall on a new run)
        current_room_obj = house.get_room_by_name("ENTRANCE HALL")
        return current_room_obj
    else:
        current_room_name = get_current_room_name(reader)
        current_room_obj = None
        current_room_obj = house.get_room_by_name(current_room_name)
        if current_room_obj:
            return current_room_obj
        else:
            print(f"\nCurrent room '{current_room_name}' not found in HOUSE. Prompting user for manual input...")
            current_room_obj = house.prompt_for_room_name(current_room_name)
            return current_room_obj

def get_current_room_name(reader: easyocr.Reader) -> str:
    """
        Extract current room name from screen using OCR

            Args:
                reader: Initialized EasyOCR reader for text recognition

            Returns:
                Name of the current room
    """
    bbox = REGIONS["other"]["current_room"]
    current_room_screenshot = ScreenCapture(bbox).run()
    current_room_screenshot = np.array(current_room_screenshot)
    current_room_screenshot = cv2.cvtColor(current_room_screenshot, cv2.COLOR_RGB2BGR)
    results = easy_ocr(reader, current_room_screenshot, False, ALPHANUMERIC_ALLOWLIST)
    for _, text, _ in results:
        current_room = best_match(text, list(ROOM_LOOKUP.keys()))
        if current_room:
            return current_room
    print("CURRENT ROOM unable to be detected by OCR. Prompting user for manual input...")
    time.sleep(1) 
    while True:
        room_name = input("\nPlease enter your current room name: ").strip().upper()
        if room_name in ROOM_LOOKUP:
            return room_name
        print("\nInvalid room name. Please try again.")
        time.sleep(2)