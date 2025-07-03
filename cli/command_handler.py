"""
Command handlers for menu options.
"""
from typing import Optional

import easyocr
from google.cloud import vision

from capture.items import capture_items
from capture.note_capture import capture_note
from capture.resources import capture_resources
from capture.shops import stock_shelves
from cli.drafting_handler import DraftingHandler
from llm.llm_agent import BluePrinceAgent
from llm.llm_parsers import parse_note_title_response

from .action_handler import ActionHandler
from .decorators import auto_save, capture_resources_first, requires_current_room, handle_command_safely, requires_shop_room


class CommandHandler:
    """Handles all menu command implementations."""
    
    def __init__(self, agent: BluePrinceAgent, google_client: vision.ImageAnnotatorClient, reader: easyocr.Reader, editor_path: Optional[str]) -> None:
        self.agent = agent
        self.google_client = google_client
        self.reader = reader
        self.editor_path = editor_path
        self.action_handler = ActionHandler(agent, google_client, reader, editor_path)
        self.drafting_handler = DraftingHandler(agent, google_client, reader)

    @handle_command_safely
    @auto_save
    def capture_resources(self) -> bool:
        """Capture resources using OCR."""
        print("Capturing resources...")
        current_resources = capture_resources(self.google_client, self.agent.game_state.resources)
        self.agent.game_state.resources.update(current_resources)
        print("Resources captured and saved.")
        return True

    @handle_command_safely
    @requires_current_room
    def capture_note(self) -> bool:
        """Capture a note for the current room."""
        print("Capturing note...")
        note = capture_note(self.google_client, self.agent.game_state.current_room, self.editor_path)  # type: ignore
        response = self.agent.generate_note_title(note.content)
        parsed_response = parse_note_title_response(response)
        note.title = parsed_response
        self.agent.note_memory.add_to_json(note)
        print("Note captured and saved.")
        return True

    @handle_command_safely
    @auto_save
    def capture_items(self) -> bool:
        """Capture items using OCR."""
        print("Capturing items...")
        item_val = capture_items(self.google_client)
        if item_val == "Screenshot capture was cancelled.":
            print(item_val)
        elif isinstance(item_val, dict):
            current_item, item_description = next(iter(item_val.items()))
            self.agent.game_state.items.update({current_item: item_description})
            self.agent.term_memory.automated_add_term(current_item, item_description)
            print("Items captured and saved.")
        elif item_val is None:
            print("No item was captured.")
        else:
            print(f"Unexpected return value: {item_val}")
        return True

    @handle_command_safely
    @requires_current_room
    @requires_shop_room
    @auto_save
    def stock_shelves(self) -> bool:
        """Stock shelves in the current room."""
        print("Stocking shelves...")
        stock_shelves(self.reader, self.agent.game_state.current_room)  # type: ignore
        print("Shelves stocked.")
        return True

    @handle_command_safely
    @capture_resources_first
    @requires_current_room
    def take_action(self) -> bool:
        """Use LLM to decide on actions based on current state."""
        return self.action_handler.handle_take_action()

    @handle_command_safely
    @capture_resources_first
    @requires_current_room
    @auto_save
    def drafting_options(self) -> bool:
        """Capture drafting options for the current room."""
        return self.drafting_handler.handle_drafting_options()

    @handle_command_safely
    def add_term_to_memory(self) -> bool:
        """Add a term to memory."""
        self.agent.term_memory.user_facilitated_add_term()
        return True

    @handle_command_safely
    @requires_current_room
    @auto_save
    def set_dig_spots(self) -> bool:        #TODO: allow for any room.. not just current
        """Set dig spots in the current room."""
        self.agent.game_state.current_room.set_dig_spots()  # type: ignore
        return True

    @handle_command_safely
    @requires_current_room
    @auto_save
    def set_trunks(self) -> bool:        #TODO: allow for any room.. not just current
        """Set trunks in the current room."""
        self.agent.game_state.current_room.set_trunks()  # type: ignore
        return True

    @handle_command_safely
    @requires_current_room
    @auto_save
    def edit_doors(self) -> bool:
        """Edit doors in the current room."""
        self.agent.game_state.current_room.edit_doors()  # type: ignore
        self.agent.game_state.house.connect_adjacent_doors(self.agent.game_state.current_room)  # type: ignore
        self.agent.game_state.house.update_security_doors()
        return True

    @handle_command_safely
    @requires_current_room
    @requires_shop_room
    @auto_save
    def edit_items_for_sale(self) -> bool:
        """Edit items for sale in the current room."""
        self.agent.game_state.current_room.edit_items_for_sale()  # type: ignore
        return True

    @handle_command_safely
    @auto_save
    def fill_room_attributes(self) -> bool:
        """Autofill attributes for a room based on its position."""
        potential_rooms_to_edit = self.agent.game_state.house.get_rooms_by_name("UNKNOWN")
        
        if not potential_rooms_to_edit:
            print("No rooms to autofill attributes for.")
            return False
        
        if len(potential_rooms_to_edit) == 1:
            room_to_edit = potential_rooms_to_edit[0]
        else:
            print("Select a room to edit:")
            for idx, room in enumerate(potential_rooms_to_edit):
                print(f"{idx + 1}: Position: {room.position}")
                
            selection = input("Enter the number of the room to edit: ").strip()
            if selection.isdigit() and 1 <= int(selection) <= len(potential_rooms_to_edit):
                room_to_edit = potential_rooms_to_edit[int(selection) - 1]
            else:
                print("Invalid selection.")
                return False
        
        room_name = input("Please enter the name of the room: ").strip().upper()
        self.agent.game_state.house.generic_autofill_room_attributes(room_to_edit, room_name)
        room_to_edit = self.agent.game_state.house.specialize_room(room_to_edit)
        self.agent.game_state.house.update_room_in_house(room_to_edit)
        self.agent.room_memory.add_room(room_to_edit)
        print(f"Room updated to {room_name}.")
        return True

    @handle_command_safely
    def manual_llm_follow_up(self) -> bool:
        """Analyze previous LLM decision."""
        response = self.agent.manual_llm_follow_up()
        print(f"\nManual LLM Follow Up Response:\n{response}")
        return True

    @handle_command_safely
    def call_it_a_day(self) -> bool:
        """End the current run and save progress."""
        return self.action_handler._handle_call_it_a_day()