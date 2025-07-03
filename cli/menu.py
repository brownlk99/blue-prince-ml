"""
Main menu and command dispatch.
"""
import time
from typing import Optional

import easyocr
from google.cloud import vision

from llm.llm_agent import BluePrinceAgent
from .command_handler import CommandHandler

# Menu configuration
MENU_OPTIONS = {
    '1': ('capture_resources', 'Capture Resources - Use OCR to capture and update resource counts.'),
    '2': ('capture_note', 'Capture Note - Capture a note for the current room.'),
    '3': ('capture_items', 'Capture Items - Use OCR to capture and update items.'),
    '4': ('stock_shelves', 'Stock Shelves - Stock shelves in the current room.'),
    '5': ('take_action', 'Take Action - Use LLM to decide on actions based on current state.'),
    '6': ('drafting_options', 'Drafting Options - Capture drafting options for the current room.'),
    '7': ('add_term_to_memory', 'Add Term to Memory - Add a term to memory.'),
    '8': ('set_dig_spots', 'Set Dig Spots - Set dig spots in the current room.'),
    '9': ('set_trunks', 'Set Trunks - Set trunks in the current room.'),
    '10': ('edit_doors', 'Edit Doors - Edit doors in the current room.'),
    '11': ('edit_items_for_sale', 'Edit Items for Sale - Edit items for sale in the current room.'),
    '12': ('fill_room_attributes', 'Fill Room Attributes - Autofill attributes for a room based on its position.'),
    '13': ('manual_llm_follow_up', 'Manual LLM Follow Up - Analyze previous LLM decision.'),
    '14': ('call_it_a_day', 'Call It a Day - End the current run and save progress.'),
}

MENU_HEADER = """
=========== Blue Prince ML Control Menu ==========="""

MENU_FOOTER = """
q. Quit                     - Exit the script.
"""

CURRENT_RUN_FILE = './jsons/current_run.json'

class CliMenu:
    """Main game menu and command dispatcher."""
    
    def __init__(self, agent: BluePrinceAgent, google_client: vision.ImageAnnotatorClient, reader: easyocr.Reader, editor_path: Optional[str]) -> None:
        self.command_handler = CommandHandler(agent, google_client, reader, editor_path)

    def print_menu(self) -> None:
        """Print the main menu options."""
        print(MENU_HEADER)
        for key, (_, description) in MENU_OPTIONS.items():
            print(f"{key}. {description}")
        print(MENU_FOOTER)

    def execute_command(self, command_key: str) -> bool:
        """Execute a command based on the menu selection."""
        if command_key in MENU_OPTIONS:
            method_name, _ = MENU_OPTIONS[command_key]
            if hasattr(self.command_handler, method_name):
                method = getattr(self.command_handler, method_name)
                try:
                    result = method()
                    return result if result is not None else True
                except Exception as e:
                    print(f"Error executing command '{method_name}': {e}")
                    return False
            else:
                print(f"Command method '{method_name}' not implemented.")
                return False
        return False

    def run(self) -> None:
        """Run the main menu loop."""
        print("Script is running. Type a number (1-14) and press Enter to interact. Type 'q' to quit.")
        
        while True:
            self.print_menu()
            user_input = input("\nEnter command (1-14, q to quit): ").strip().lower()
            
            if user_input == 'q':
                print("Exiting script.")
                break

            if user_input not in MENU_OPTIONS:
                print("Invalid input. Please enter a number between 1 and 15, or 'q' to quit.")
            else:
                success = self.execute_command(user_input)
                if not success:
                    print("Command failed to execute. Please check your current state and try again.")
                    
            # Small pause for readability
            time.sleep(1) 