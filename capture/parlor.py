from typing import Optional

import cv2
import easyocr
import numpy as np

from capture.constants import ALPHANUMERIC_ALLOWLIST
from capture.ocr import easy_ocr
from capture.screen_capture import ScreenCapture
from capture.vision_utils import edit_text_in_editor, generic_autocorrect


def capture_hint(reader: easyocr.Reader, editor_path: Optional[str] = None) -> str:
    """
        Capture and process a puzzle hint from the screen using OCR

            Args:
                reader (easyocr.Reader): Initialized EasyOCR reader for text recognition
                editor_path (Optional[str]): Path to text editor for manual editing

            Returns:
                str: Processed and edited hint text
    """
    puzzle_hint_screenshot = ScreenCapture().run()
    puzzle_hint_screenshot = np.array(puzzle_hint_screenshot)
    puzzle_hint_screenshot = cv2.cvtColor(puzzle_hint_screenshot, cv2.COLOR_RGB2BGR)
    results = easy_ocr(reader, puzzle_hint_screenshot, True, ALPHANUMERIC_ALLOWLIST)
    for _, text in results:
        if text:
            autocorrected_text = generic_autocorrect(text).upper()
            edited_text = edit_text_in_editor(autocorrected_text, editor_path)
        else:
            edited_text = ""
    return edited_text
