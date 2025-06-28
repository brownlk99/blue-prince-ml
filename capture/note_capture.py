import os
import subprocess
import tempfile
import threading
import time
from typing import Optional
import cv2
import numpy as np
import mouse
from mouse import ButtonEvent
from threading import Event
from note import Note
from room import Room
from capture.screen_capture import ScreenCapture
from google.cloud import vision
from capture.ocr import google_vision
from capture.vision_utils import edit_text_in_editor, generic_autocorrect


def capture_and_process_helper(client: vision.ImageAnnotatorClient, pages: list[str], editor_path: Optional[str] = None) -> None:
    time.sleep(1)  # Allow time so there's no overlap with clicking to activate and triggering the capture
    note_screenshot = ScreenCapture().run()
    if note_screenshot is None:
        print("Screenshot failed or was cancelled.")
        return

    note_screenshot = np.array(note_screenshot)
    note_screenshot = cv2.cvtColor(note_screenshot, cv2.COLOR_RGB2BGR)
    note_text = google_vision(client, note_screenshot)
    corrected_note_text = generic_autocorrect(note_text)
    edited_page = edit_text_in_editor(corrected_note_text, editor_path)
    pages.append(edited_page)
    print()

def capture_note(client: vision.ImageAnnotatorClient, current_room: Room, editor_path: Optional[str] = None) -> Note:
    print("Starting note capture with mouse input.")
    pages = []

    # Capture the first page immediately
    capture_and_process_helper(client, pages, editor_path)
    print("Left click to capture next page. Right click to finish note capture.")

    stop_capture = Event()       # Used to signal when to stop capturing
    hook_ref: list = [None]            # Holds the current mouse hook reference (list allows mutation in nested scope)

    def on_mouse(event):
        # Only respond to actual mouse button down events (ignore movement or button-up)
        if not isinstance(event, mouse.ButtonEvent):
            return
        if event.event_type != 'down':
            return

        # Safely unhook the current mouse listener if it exists
        if hook_ref[0] is not None:
            mouse.unhook(hook_ref[0])
            hook_ref[0] = None  # Clear the reference to prevent unhooking twice

        if event.button == 'left':
            print("Left click detected — capturing next page.")
            capture_and_process_helper(client, pages, editor_path)
            print("Left click to capture next page. Right click to finish note capture.")
            # Delay re-hooking the listener in a background thread (avoids GUI click bleed-over)
            def delayed_rehook():
                time.sleep(0.5)  # Let the OS settle the click queue
                if not stop_capture.is_set():  # Only rehook if capture session is still active
                    hook_ref[0] = mouse.hook(on_mouse)  # Re-register the listener

            threading.Thread(target=delayed_rehook, daemon=True).start()

        elif event.button == 'right':
            print("Right click detected — finishing note capture.")
            stop_capture.set()  # This will break the capture loop below

    # Register the initial mouse hook and store its reference
    hook_ref[0] = mouse.hook(on_mouse)

    try:
        # Keep looping until right-click signals we're done
        while not stop_capture.is_set():
            time.sleep(0.1)
    finally:
        # Clean up hook if still active (e.g. if right-click didn't already unhook)
        if hook_ref[0] is not None:
            mouse.unhook(hook_ref[0])

    full_content = "\n\n".join(pages)

    # color capture (manual for now)
    acceptable_colors = ["RED", "BLUE", "GREEN", "YELLOW", "WHITE", "BLACK"]
    color = input("Enter the color of the note (e.g., 'RED', 'BLUE', etc.): ").strip().upper()
    while color not in acceptable_colors:
        print(f"\nInvalid color. Please choose from: {', '.join(acceptable_colors)}")
        time.sleep(2)
        color = input("Enter the color of the note (e.g., 'RED', 'BLUE', etc.): ").strip().upper()
    note = Note(content=full_content, found_in_room=current_room.name, color=color)
    return note