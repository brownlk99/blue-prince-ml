"""
Main menu and command dispatch.
"""
import time
from typing import Optional

import easyocr
from google.cloud import vision

from cli.command_handler import CommandHandler
from llm.llm_agent import BluePrinceAgent

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
    '14': ('show_house_map', 'Show House Map - Display the current house layout with door states.'),
    '15': ('call_it_a_day', 'Call It a Day - End the current run and save progress.'),
}

MENU_HEADER = """
=========== Blue Prince ML Control Menu ==========="""

MENU_FOOTER = """
q. Quit                    - Exit the script.
"""

CURRENT_RUN_FILE = './jsons/current_run.json'

class CliMenu:
    """
        Main game menu and command dispatcher for user interactions

            Attributes:
                command_handler: Handler for executing menu commands
                verbose: Whether to show verbose error information
    """
    
    def __init__(self, agent: BluePrinceAgent, google_client: vision.ImageAnnotatorClient, reader: easyocr.Reader, editor_path: Optional[str], verbose: bool = False) -> None:
        """
            Initialize CliMenu with required dependencies for menu operations and command handling

                Args:
                    agent: The LLM agent for making decisions
                    google_client: Google Vision API client for OCR
                    reader: EasyOCR reader for text recognition
                    editor_path: Path to text editor for manual editing
                    verbose: Whether to show verbose error information
        """
        self.command_handler = CommandHandler(agent, google_client, reader, editor_path)
        self.verbose = verbose

    def print_menu(self) -> None:
        """
            Print the main menu options with formatted display
        """
        print(MENU_HEADER)
        
        # find the longest command name to determine padding
        max_command_length = 0
        commands = {}
        
        for key, (_, description) in MENU_OPTIONS.items():
            # split on first " - " to separate command from description
            parts = description.split(' - ', 1)
            command_name = parts[0]
            desc = parts[1] if len(parts) > 1 else ""
            commands[key] = (command_name, desc)
            max_command_length = max(max_command_length, len(command_name))
        
        # print each option with proper spacing
        for key, (command_name, desc) in commands.items():
            padded_command = command_name.ljust(max_command_length)
            print(f"{key:>2}. {padded_command}   - {desc}")
        
        print(MENU_FOOTER)

    def execute_command(self, command_key: str) -> bool:
        """
            Execute a command based on the menu selection

                Args:
                    command_key: The menu option key selected by user

                Returns:
                    True if command was executed successfully
        """
        if command_key in MENU_OPTIONS:
            method_name, _ = MENU_OPTIONS[command_key]
            if hasattr(self.command_handler, method_name):
                method = getattr(self.command_handler, method_name)
                try:
                    result = method()
                    return result if result is not None else True
                except Exception as e:
                    self._handle_command_error(method_name, e)
                    return False
            else:
                print(f"Command method '{method_name}' not implemented.")
                return False
        return False

    def _handle_command_error(self, command_name: str, error: Exception) -> None:
        """
            Handle and display user-friendly error messages

                Args:
                    command_name: Name of the command that failed
                    error: The exception that occurred
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # check for common error patterns and provide friendly messages
        if "google.api_core.exceptions.ServiceUnavailable" in str(type(error)):
            print(f"\nNetwork Error: Unable to connect to Google Vision API")
            print("   This is usually a temporary connection issue. Please try again in a moment.")
            
        elif "IOCP/Socket: Connection reset" in error_msg or "Connection reset" in error_msg:
            print(f"\nConnection Error: Network connection was interrupted")
            print("   Please check your internet connection and try again.")
            
        elif "grpc" in error_msg.lower():
            print(f"\nAPI Communication Error: Unable to communicate with external services")
            print("   This might be a temporary issue. Please try again.")
            
        elif "FileNotFoundError" in error_type:
            print(f"\nFile Error: Required file not found")
            print(f"   {error_msg}")
            
        elif "PermissionError" in error_type:
            print(f"\nPermission Error: Unable to access required files")
            print("   Please check file permissions or close any programs using the files.")
            
        elif "KeyError" in error_type:
            print(f"\nConfiguration Error: Missing required data")
            print(f"   Key error: {error_msg}")
            
        elif "ImportError" in error_type or "ModuleNotFoundError" in error_type:
            print(f"\nModule Error: Required dependency missing")
            print(f"   {error_msg}")
            
        else:
            # generic error with shortened message
            print(f"\n{command_name.replace('_', ' ').title()} Failed")
            # show only the last line of the error message (usually the most relevant)
            clean_msg = error_msg.split('\n')[-1] if '\n' in error_msg else error_msg
            if len(clean_msg) > 100:
                clean_msg = clean_msg[:97] + "..."
            print(f"   Error: {clean_msg}")
        
        # only show debug info in verbose mode
        if self.verbose:
            print(f"   (Debug: {error_type})")
            if len(error_msg) > 200:  # show more detail in verbose mode
                print(f"   (Full error: {error_msg[:200]}...)")

    def run(self) -> None:
        """
            Run the main menu loop and handle user interactions

                Returns:
                    None
        """
        print("Script is running. Type a number (1-15) and press Enter to interact. Type 'q' to quit.")
        
        while True:
            self.print_menu()
            user_input = input("\nEnter command (1-15, q to quit): ").strip().lower()
            
            if user_input == 'q':
                print("Exiting script.")
                break

            if user_input not in MENU_OPTIONS:
                print("Invalid input. Please enter a number between 1 and 15, or 'q' to quit.")
            else:
                success = self.execute_command(user_input)
                if not success:
                    print("\nYou can try the command again or choose a different option.")
                    
            # small pause for readability
            time.sleep(1) 