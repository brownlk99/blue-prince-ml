from typing import Optional

import cv2
import numpy as np
from google.cloud import vision

from capture.constants import REGIONS
from capture.ocr import google_vision
from capture.screen_capture import ScreenCapture
from capture.vision_utils import generic_autocorrect, edit_text_in_editor


def capture_lab_experiment_options(google_client: vision.ImageAnnotatorClient, editor_path: Optional[str] = None) -> dict:
    """
        Capture options for the lab experiment

            Args:
                google_client (vision.ImageAnnotatorClient): Google Vision API client
                editor_path (Optional[str]): Path to the text editor to use

            Returns:
                dict: A dictionary containing the options for the lab experiment
    """
    options = {"causes": [], "effects": []}
    for type, list in REGIONS["laboratory"].items():
        for region in list:
            screenshot = ScreenCapture(region).run()
            screenshot = np.array(screenshot)
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            text = google_vision(google_client, screenshot)
            autocorrected_text = generic_autocorrect(text)
            edited_text = edit_text_in_editor(autocorrected_text, editor_path)
            if edited_text:
                edited_text = edited_text.strip()
                if type == "causes":
                    options["causes"].append(edited_text)
                elif type == "effects":
                    options["effects"].append(edited_text)

    return options