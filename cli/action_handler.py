"""
Action handlers for LLM-based commands.
"""
import time
from typing import Optional

import easyocr
from google.cloud import vision

from capture.constants import DIRECTORY
from capture.shops import stock_shelves
from game.room import CoatCheck
from llm.llm_agent import BluePrinceAgent
from llm.llm_parsers import (
    parse_action_response, parse_move_response, parse_door_opening_response,
    parse_purchase_response, parse_parlor_response, parse_terminal_response, parse_coat_check_response, parse_secret_passage_response
)
from utils import get_color_code

from .decorators import auto_save, requires_coat_check, requires_puzzle_room, requires_secret_passage, requires_shop_room, requires_utility_closet
from .terminal_handler import TerminalCommandProcessor


class ActionHandler:
    """Handles LLM-based actions."""
    
    def __init__(self, agent: BluePrinceAgent, google_client: vision.ImageAnnotatorClient, reader: easyocr.Reader, editor_path: Optional[str]) -> None:
        self.agent = agent
        self.google_client = google_client
        self.reader = reader
        self.editor_path = editor_path
        self.terminal_processor = TerminalCommandProcessor(agent, google_client, editor_path)


    def handle_take_action(self) -> bool:
        """Handle the main LLM action decision process."""
        self.agent.game_state.current_position = self.agent.game_state.current_room.position  # type: ignore

        context = self.agent.game_state.summarize_for_llm()
        response = self.agent.take_action(context)
        parsed_response = parse_action_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"Action Response:\nAction: {parsed_response['action']}\nExplanation: {parsed_response['explanation']}")
        time.sleep(2)

        action = parsed_response["action"]
        
        if action == "move":
            return self._handle_move_action(context)
        elif action == "open_door":
            return self._handle_door_action(context)
        elif action == "peruse_shop":
            return self._handle_peruse_shop_action()
        elif action == "purchase_item":
            return self._handle_purchase_action(context)
        elif action == "solve_puzzle":
            return self._handle_solve_puzzle_action(context)
        elif action == "open_secret_passage":
            return self._handle_secret_passage_action(context)
        elif action == "dig":
            return self._handle_dig_action()
        elif action == "open_trunk":
            return self._handle_trunk_action()
        elif action == "use_terminal":
            return self._handle_terminal_action(context)
        elif action == "store_item_in_coat_check":
            return self._handle_store_coat_check_action(context)
        elif action == "retrieve_item_from_coat_check":
            return self._handle_retrieve_coat_check_action(context)
        elif action in ["toggle_keycard_entry_switch", "toggle_gymnasium_switch", "toggle_darkroom_switch", "toggle_garage_switch"]:
            return self._handle_switch_action(action)
        elif action == "call_it_a_day":
            return self._handle_call_it_a_day()
        else:
            print(f"Unknown action: {action}")
            return False

    def _handle_move_action(self, context: str) -> bool:
        """Handle move action."""
        response = self.agent.decide_move(context)
        parsed_response = parse_move_response(response)
        parsed_response["action"] = "move"
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"\nMove Response:\nTarget Room: {get_color_code(parsed_response['target_room'])}\nPath: {parsed_response['path']}\nPlanned Action: {parsed_response['planned_action']}\nExplanation: {parsed_response['explanation']}")
        time.sleep(2)
        return True

    @auto_save
    def _handle_door_action(self, context: str) -> bool:
        """Handle door opening action."""
        response = self.agent.decide_door_to_open(context)
        parsed_response = parse_door_opening_response(response, self.agent)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"\nDoor Opening Response:\nDirection: {parsed_response['door_direction']}\nSpecial Item: {parsed_response['special_item']}\nExplanation: {parsed_response['explanation']}")
        
        if parsed_response["special_item"] != "NONE":
            if parsed_response["special_item"] in self.agent.game_state.items.keys():
                self.agent.game_state.items.pop(parsed_response["special_item"])
                print(f"Used {parsed_response['special_item']}")
            else:
                print(f"Special item {parsed_response['special_item']} not found in inventory.")
        time.sleep(2)
        return True

    @requires_shop_room
    @auto_save
    def _handle_peruse_shop_action(self) -> bool:
        """Handle peruse shop action."""
        input(f"\nPlease access the {self.agent.game_state.current_room.name} shop inventory and press 'Enter' to stock shelves: ")  # type: ignore
        stock_shelves(self.reader, self.agent.game_state.current_room)  # type: ignore
        print("\nStocked shelves")
        return True

    @requires_shop_room
    @auto_save
    def _handle_purchase_action(self, context: str) -> bool:
        """Handle purchase item action."""
        response = self.agent.decide_purchase_item(context)
        parsed_response = parse_purchase_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"Purchase Response:\nItem: {parsed_response['item']}\nQuantity: {parsed_response['quantity']}\nExplanation: {parsed_response['explanation']}")
        self.agent.game_state.purchase_item()
        return True

    @requires_puzzle_room
    @auto_save
    def _handle_solve_puzzle_action(self, context: str) -> bool:
        """Handle solve puzzle action."""
        response = self.agent.solve_parlor_puzzle(self.reader, context, self.editor_path)
        parsed_response = parse_parlor_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"Parlor Response:\nBox: {get_color_code(parsed_response['box'])}\nExplanation: {parsed_response['explanation']}")
        self.agent.game_state.current_room.has_been_solved = True  # type: ignore
        return True

    @requires_secret_passage
    @auto_save
    def _handle_secret_passage_action(self, context: str) -> bool:
        """Handle open secret passage action."""
        response = self.agent.open_secret_passage(context)
        parsed_response = parse_secret_passage_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"Secret Passage Response:\nRoom Type: {parsed_response['room_type']}\nExplanation: {parsed_response['explanation']}")
        self.agent.game_state.current_room.has_been_used = True  # type: ignore
        return True

    @auto_save
    def _handle_dig_action(self) -> bool:
        """Handle dig action."""
        self.agent.game_state.current_room.set_dig_spots()  # type: ignore
        return True

    @auto_save
    def _handle_trunk_action(self) -> bool:
        """Handle open trunk action."""
        self.agent.game_state.current_room.set_trunks()  # type: ignore
        return True

    def _handle_terminal_action(self, context: str) -> bool:
        """Handle use terminal action."""
        response = self.agent.use_terminal(context)
        parsed_response = parse_terminal_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"Terminal Response:\nCommand: {parsed_response['command']}\nExplanation: {parsed_response['explanation']}")
        
        command = parsed_response.get("command", "").upper()
        return self.terminal_processor.process_terminal_command(command, context)

    @requires_coat_check
    @auto_save
    def _handle_store_coat_check_action(self, context: str) -> bool:
        """Handle store item in coat check action."""
        response = self.agent.coat_check_prompt("STORE", context)
        parsed = parse_coat_check_response(response)
        parsed["context"] = context
        self.agent.decision_memory.add_decision(parsed)
        print(f"Coat Check Response:\nItem: {parsed['item']}\nExplanation: {parsed['explanation']}")

        if parsed["item"] not in self.agent.game_state.items:
            print(f"Item {parsed['item']} not found in inventory.")
            return False
        
        self.agent.game_state.current_room.stored_item = parsed["item"]  # type: ignore
        self.agent.game_state.items.pop(parsed["item"])

        print(f"Stored {parsed['item']} in Coat Check.")
        return True

    @requires_coat_check
    @auto_save
    def _handle_retrieve_coat_check_action(self, context: str) -> bool:
        """Handle retrieve item from coat check action."""
        response = self.agent.coat_check_prompt("RETRIEVE", context)
        parsed_response = parse_coat_check_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"Coat Check Response:\nItem: {parsed_response['item']}\nExplanation: {parsed_response['explanation']}")
        
        if parsed_response["item"] not in self.agent.game_state.current_room.stored_item or parsed_response["item"] not in DIRECTORY["ITEMS"]:  # type: ignore
            print(f"Item {parsed_response['item']} not found in Coat Check.")
            return False
        
        self.agent.game_state.items[parsed_response["item"]] = DIRECTORY["ITEMS"][parsed_response["item"]]
        self.agent.game_state.current_room.stored_item = ""  # type: ignore
        print(f"Retrieved {parsed_response['item']} from Coat Check.")
        return True

    @requires_utility_closet
    @auto_save
    def _handle_switch_action(self, action: str) -> bool:
        """Handle utility closet switch actions."""
        switch_name = action.replace("toggle_", "")
        self.agent.game_state.current_room.toggle_switch(switch_name)  # type: ignore
        if switch_name == "keycard_entry_system_switch":
            self.agent.game_state.house.update_security_doors()
        print(f"Toggled {switch_name}")
        return True

    @auto_save
    def _handle_call_it_a_day(self) -> bool:
        """End the current run and save progress."""
        
        # Save the final state for this day
        self.agent.game_state.save(f'./jsons/runs/day_{self.agent.game_state.day}.json')

        reason_for_ending = input("Reason for ending the run: ")

        # Determine what item is in the coat check for the next run
        coat_check = self.agent.game_state.house.get_room_by_name("COAT CHECK")
        previous_run = self.agent.previous_run_memory.get_most_recent_run()
        previous_stored_item = previous_run.get("stored_item", "")
        stored_item = ""

        if isinstance(coat_check, CoatCheck):
            # Player interacted with coat check this run
            current_stored_item = coat_check.stored_item

            if current_stored_item != previous_stored_item:
                # Player swapped out or added a new item
                stored_item = current_stored_item
            else:
                # Player did not exchange any item, keep previous
                stored_item = previous_stored_item
        else:
            # Coat check not present, keep previous stored item
            stored_item = previous_stored_item

        self.agent.previous_run_memory.add_run(self.agent.game_state.day, reason_for_ending, stored_item)
        print(f"\nDay {self.agent.game_state.day} has ended. Run data saved.")
        return True 
