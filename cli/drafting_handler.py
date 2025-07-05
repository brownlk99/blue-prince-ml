import time
from typing import List, Union, Literal

import easyocr
from google.cloud import vision

from capture.drafting import capture_drafting_options
from game.room import Room
from llm.llm_agent import BluePrinceAgent
from llm.llm_parsers import parse_drafting_response
from utils import get_color_code


class DraftingHandler:
    """
        Handles drafting operations and room selection logic

            Attributes:
                agent: The LLM agent for making decisions
                google_client: Google Vision API client for OCR
                reader: EasyOCR reader for text recognition
    """
    
    def __init__(self, agent: BluePrinceAgent, google_client: vision.ImageAnnotatorClient, reader: easyocr.Reader) -> None:
        """
            Initialize DraftingHandler with required dependencies for drafting operations

                Args:
                    agent: The LLM agent for making decisions
                    google_client: Google Vision API client for OCR
                    reader: EasyOCR reader for text recognition
        """
        self.agent = agent
        self.google_client = google_client
        self.reader = reader

    def handle_drafting_options(self) -> bool:
        """
            Handle drafting options capture and selection process

                Returns:
                    True if drafting options were handled successfully
        """
        self.agent.game_state.current_position = self.agent.game_state.current_room.position  # type: ignore

        # Get the previously chosen room and door from the agent
        room = self.agent.game_state.house.get_room_by_name(self.agent.previously_chosen_room)
        if room is not None:
            chosen_door = room.get_door_by_orientation(self.agent.previously_chosen_door)
        else:
            print("Previously chosen room not found, cannot DRAFT.")
            return False

        while True:
            drafting_options = capture_drafting_options(self.reader, self.google_client, room, chosen_door)
            context = self.agent.game_state.summarize_for_llm()
            response = self.agent.decide_drafting_option(drafting_options, context)
            parsed_response = parse_drafting_response(response)
            parsed_response["context"] = context
            self.agent.decision_memory.add_decision(parsed_response)
        
            if "action" in parsed_response:
                print(f"Drafting Response:\nAction: {parsed_response['action']}\nType: {parsed_response['type']}\nExplanation: {parsed_response['explanation']}")
                input("\nPress 'Enter' after you have REDRAWN: ")
                continue
            elif "room" in parsed_response:
                result = self._handle_room_selection(parsed_response, drafting_options)
                if result == "RETRY":
                    continue
                else:
                    return result
            else:
                print("Invalid drafting response format.")
                return False

    def _handle_room_selection(self, parsed_response: dict, drafting_options: List[Room]) -> Union[bool, Literal["RETRY"]]:
        """
            Handle room selection from drafting options and process the choice

                Args:
                    parsed_response: Parsed LLM response containing room selection
                    drafting_options: Available room options to choose from

                Returns:
                    True if successful, False if failed, "RETRY" if should retry
        """
        print(f"Drafting Response:\nRoom: {get_color_code(parsed_response['room'])}\nEnter: {get_color_code(parsed_response['enter'])}\nExplanation: {parsed_response['explanation']}")
        
        # check if we're dealing with unknown rooms
        all_unknown = all(option.name == "UNKNOWN" for option in drafting_options)
        selected_room = None
        
        if all_unknown:
            # handle case where all rooms are UNKNOWN (dark room effect)
            print("All drafts are UNKNOWN due to dark room effect. Using generic UNKNOWN room.")
            selected_room = drafting_options[0]
        else:
            # find the room that matches the LLM's selection
            room_name = parsed_response["room"].upper()
            selected_room = next((room for room in drafting_options if room.name == room_name), None)
            
            if not selected_room:
                print(f"Error: Selected room '{room_name}' not found in drafting options.")
                return "RETRY"
        
        # check if player can afford the room
        if selected_room.cost > self.agent.game_state.resources.get("gems", 0):
            print(f"\nNot enough resources to draft {selected_room.name}. Cost: {selected_room.cost}, Available: {self.agent.game_state.resources.get('gems', 0)}")
            return "RETRY"

        if selected_room.name == "UNKNOWN" or selected_room.name == "ARCHIVED FLOOR PLAN":
            room_name = input("Please enter the name of the newly drafted room: ").strip().upper()
            self.agent.game_state.house.generic_autofill_room_attributes(selected_room, room_name)
            selected_room = self.agent.game_state.house.specialize_room(selected_room)

        # add room to house and handle additional operations
        self.agent.game_state.house.add_room_to_house(selected_room)
        self.agent.game_state.house.connect_adjacent_doors(selected_room)
        self.agent.room_memory.add_room(selected_room)

        # handle room entry if requested
        if parsed_response.get("enter", "").upper() == "YES":
            selected_room.has_been_entered = True
            if len(selected_room.doors) > 1:
                print("\nPlease enter the room and edit the doors within the newly drafted room to ensure accuracy.")
                time.sleep(2)
                selected_room.edit_doors()

        self.agent.game_state.house.update_security_doors()
        self.agent.game_state.house.print_map()
        return True 