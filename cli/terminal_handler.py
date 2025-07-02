"""
Terminal command processors.
"""
from typing import Optional

from google.cloud import vision

from capture.lab import capture_lab_experiment_options
from game.room import Security, Office, Laboratory, Shelter
from llm.llm_agent import BluePrinceAgent
from llm.llm_parsers import (
    parse_lab_experiment_response,
    parse_security_level_response,
    parse_mode_response
)

from .constants import TERMINAL_COMMANDS


class TerminalCommandProcessor:
    """Handles terminal command processing."""
    
    def __init__(self, agent: BluePrinceAgent, google_client: vision.ImageAnnotatorClient, editor_path: Optional[str]) -> None:
        self.agent = agent
        self.google_client = google_client
        self.editor_path = editor_path

    def process_terminal_command(self, command: str, context: str) -> bool:
        """Process a terminal command and return success status."""
        command = command.upper()
        
        if command == "RUN EXPERIMENT SETUP":
            return self.handle_lab_experiment(context)
        elif command == "VIEW ESTATE INVENTORY":
            return self.handle_estate_inventory()
        elif command == "ALTER SECURITY LEVEL":
            return self.handle_security_level(context)
        elif command == "ALTER MODE":
            return self.handle_mode(context)
        elif command == "RUN PAYROLL":
            return self.handle_payroll()
        elif command == "SPREAD GOLD IN ESTATE":
            return self.handle_gold_spread()
        elif command == "TIME LOCK SAFE":
            return self.handle_time_lock_safe()
        else:
            print(f"Unknown terminal command: {command}")
            return False

    def handle_lab_experiment(self, context: str) -> bool:
        """Handle laboratory experiment setup."""
        options = capture_lab_experiment_options(self.google_client, self.editor_path)
        response = self.agent.decide_lab_experiment(options, context)
        parsed_response = parse_lab_experiment_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"Lab Experiment Response:\nCause: {parsed_response.get('cause', 'N/A')}\nEffect: {parsed_response.get('effect', 'N/A')}\nExplanation: {parsed_response.get('explanation', 'N/A')}")
        return True

    def handle_estate_inventory(self) -> bool:
        """Handle viewing estate inventory."""
        if isinstance(self.agent.game_state.current_room, Security):
            self.agent.game_state.current_room.terminal.set_estate_inventory()
            return True
        else:
            print("Current room does not have a SECURITY TERMINAL, cannot view estate inventory.")
            return False

    def handle_security_level(self, context: str) -> bool:
        """Handle altering security level."""
        response = self.agent.decide_security_level(context)
        parsed_response = parse_security_level_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"Security Level Response:\nLevel: {parsed_response['security_level']}\nExplanation: {parsed_response['explanation']}")
        
        if isinstance(self.agent.game_state.current_room, Security):
            self.agent.game_state.current_room.terminal.set_security_level(parsed_response.get("level", "MEDIUM"))
            return True
        else:
            print("Current room does not have a SECURITY TERMINAL, cannot alter security level.")
            return False

    def handle_mode(self, context: str) -> bool:
        """Handle altering security mode."""
        response = self.agent.decide_mode(context)
        parsed_response = parse_mode_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"Mode Response:\nMode: {parsed_response['mode']}\nExplanation: {parsed_response['explanation']}")
        
        if isinstance(self.agent.game_state.current_room, Security):
            self.agent.game_state.current_room.terminal.set_mode(parsed_response.get("mode", "LOCKED"))
            self.agent.game_state.house.update_security_doors()
            return True
        else:
            print("Current room does not have a SECURITY TERMINAL, cannot alter mode.")
            return False

    def handle_payroll(self) -> bool:
        """Handle running payroll."""
        if isinstance(self.agent.game_state.current_room, Office):
            self.agent.game_state.current_room.terminal.payroll_ran = True
            print("Payroll has been run.")
            return True
        else:
            print("Current room does not have an OFFICE TERMINAL, cannot run payroll.")
            return False

    def handle_gold_spread(self) -> bool:
        """Handle spreading gold in estate."""
        if isinstance(self.agent.game_state.current_room, Office):
            self.agent.game_state.current_room.terminal.gold_spread = True
            print("Gold has been spread in the estate.")
            return True
        else:
            print("Current room does not have an OFFICE TERMINAL, cannot spread gold.")
            return False

    def handle_time_lock_safe(self) -> bool:
        """Handle time lock safe command."""
        if isinstance(self.agent.game_state.current_room, Shelter):
            # TODO: SHELTER terminal still needs to be implemented
            print("SHELTER terminal time lock safe functionality not yet implemented.")
            return False
        else:
            print("Current room does not have a SHELTER TERMINAL, cannot time lock safe.")
            return False 