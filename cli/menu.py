"""
Main menu and command dispatch.
"""
import time
from typing import Optional

import easyocr
from google.cloud import vision

from llm.llm_agent import BluePrinceAgent
from .constants import MENU_OPTIONS, MENU_HEADER, MENU_FOOTER
from .command_handler import CommandHandler


class GameMenu:
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
        print("Script is running. Type a number (1-15) and press Enter to interact. Type 'q' to quit.")
        
        while True:
            self.print_menu()
            user_input = input("\nEnter command (1-15, q to quit): ").strip().lower()
            
            if user_input == 'q':
                print("Exiting script.")
                break
            
            if user_input == 'q':
                print("Exiting script.")
                break

            if user_input not in MENU_OPTIONS:
                print("Invalid input. Please enter a number between 1 and 15, or 'q' to quit.")
            else:
                success = self.execute_command(user_input)
                if not success:
                    print("Command failed to execute. Please check your current state and try again.")
            
            # Always save to file after each command (matching original behavior)
            self.command_handler.agent.game_state.save_to_file('./jsons/current_run.json')
                    
            # Small pause for readability
            time.sleep(1) 