from llm_agent import BluePrinceAgent
import time
import easyocr
import json
import argparse
from game_state import GameState
from utils import append_to_list_json, update_json
from capture.resources import capture_resources
from capture.note_capture import capture_note
from capture.vision_utils import get_current_room
from capture.drafting import capture_drafting_options
from capture.items import capture_items
from capture.shops import stock_shelves
from capture.constants import ROOM_LOOKUP

from google.cloud import vision

from door import Door
from house_map import HouseMap
from room import PuzzleRoom, Room

agent = BluePrinceAgent()
google_client = vision.ImageAnnotatorClient()
reader = easyocr.Reader(['en'], gpu=True)
agent.game_state.house.add_room_to_house(PuzzleRoom(
    name="PARLOR",
    cost=0,
    room_type=["BLUEPRINT", "PUZZLE"],
    description="This cozy lounge furnished with couches and armchairs serves as the perfect social setting for receptions and after parties. Consequently this was one of the most popular rooms for entertaining and the late H. S. Sinclair was known to supply a myriad of parlor games to encourage his guests to think and conversate.",
    additional_info="",
    shape="L",
    doors=[Door(locked=False, orientation="W", is_security=False), Door(locked=False, orientation="N", is_security=False)],
    position=(1, 8),
    rank=1
))
agent.game_state.current_position = (1, 8)
agent.game_state.current_room = agent.game_state.house.get_room_by_position(1, 8)

response = agent.take_action()
action, explanation = agent.parse_action_response(response)
print(f"Parsed Response:\nAction: {action}\nExplanation: {explanation}")