"""
Terminal command processors.
"""
from typing import Optional

from google.cloud import vision

from capture.lab import capture_lab_experiment_options
from cli.decorators import auto_save, requires_laboratory, requires_office, requires_security, requires_shelter
from llm.llm_agent import BluePrinceAgent
from llm.llm_parsers import (
    parse_lab_experiment_response,
    parse_password_guess_response,
    parse_security_level_response,
    parse_mode_response,
    parse_special_order_response
)

class TerminalCommandProcessor:
    """
        Handles terminal command processing for different room types

            Attributes:
                agent (BluePrinceAgent): The LLM agent for making decisions
                google_client (vision.ImageAnnotatorClient): Google Vision API client for OCR
                editor_path (Optional[str]): Path to text editor for manual editing
    """
    
    def __init__(self, agent: BluePrinceAgent, google_client: vision.ImageAnnotatorClient, editor_path: Optional[str]) -> None:
        self.agent = agent
        self.google_client = google_client
        self.editor_path = editor_path

    def process_terminal_command(self, command: str, context: str) -> bool:
        """
            Process a terminal command and return success status

                Args:
                    command (str): The terminal command to process
                    context (str): Current game state context

                Returns:
                    bool: True if command was processed successfully
        """
        command = command.upper()
        
        if command == "RUN EXPERIMENT SETUP":
            return self._handle_lab_experiment(context)
        elif command == "VIEW ESTATE INVENTORY":
            return self._handle_estate_inventory()
        elif command == "ALTER SECURITY LEVEL":
            return self._handle_security_level(context)
        elif command == "ALTER MODE":
            return self._handle_mode(context)
        elif command == "RUN PAYROLL":
            return self._handle_payroll()
        elif command == "SPREAD GOLD IN ESTATE":
            return self._handle_gold_spread()
        elif command == "TIME LOCK SAFE":
            return self._handle_time_lock_safe()
        elif command == "LOGIN TO THE NETWORK":
            return self._handle_login_to_network(context)
        elif command == "SPECIAL ORDERS":
            return self._handle_special_orders(context)
        else:
            print(f"Unknown terminal command: {command}")
            return False

    @auto_save
    def _handle_login_to_network(self, context: str) -> bool:
        """
            Handle login to network by having LLM guess the password

                Args:
                    context (str): Current game state context

                Returns:
                    bool: True if login was successful
        """
        current_room = self.agent.game_state.current_room
        
        if not hasattr(current_room, 'terminal'):
            print("No terminal found in current room.")
            return False
        
        terminal = current_room.terminal  # type: ignore
        
        # if already logged in, no need to guess again
        if terminal.knows_password:
            print("Already logged into network.")
            return True
        
        # have LLM guess the password
        response = self.agent.guess_network_password(context)
        parsed_response = parse_password_guess_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        
        print(f"Password Guess: {parsed_response['password']}\nExplanation: {parsed_response['explanation']}")
        
        # try the password
        success = terminal.login_to_the_network(parsed_response['password'])
        
        if success:
            print("Network access granted! Special orders are now available!")
        
        return success

    @auto_save
    def _handle_special_orders(self, context: str) -> bool:
        """
            Handle special orders command by having LLM decide what to order

                Args:
                    context (str): Current game state context

                Returns:
                    bool: True if special orders were handled successfully
        """
        current_room = self.agent.game_state.current_room
        terminal = current_room.terminal  # type: ignore
        
        available_items = terminal.get_special_order_items()
        response = self.agent.decide_special_order(available_items, context)
        parsed_response = parse_special_order_response(response)
        
        if parsed_response["item"] != "NONE":
            print(f"Special order placed: {parsed_response['item']}")
            print(f"Reasoning: {parsed_response['explanation']}")
            self.agent.game_state.special_order = parsed_response["item"]
        else:
            print("No special order placed.")
        
        return True

    @requires_laboratory
    @auto_save
    def _handle_lab_experiment(self, context: str) -> bool:
        """
            Handle laboratory experiment setup by capturing options and having LLM decide

                Args:
                    context (str): Current game state context

                Returns:
                    bool: True if lab experiment was handled successfully
        """
        options = capture_lab_experiment_options(self.google_client, self.editor_path)
        response = self.agent.decide_lab_experiment(options, context)
        parsed_response = parse_lab_experiment_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        if parsed_response.get("action") == "PAUSE EXPERIMENT":
            self.agent.game_state.current_room.terminal.set_experimental_house_feature()  # type: ignore
            print("Lab experiment paused.")
        elif parsed_response.get("action") == "EXIT":
            print("Exited lab experiment without changes.")
        else:
            self.agent.game_state.current_room.terminal.set_experimental_house_feature({"cause": parsed_response.get("cause", "N/A"), "effect": parsed_response.get("effect", "N/A")})  # type: ignore
            print(f"Lab Experiment Response:\nCause: {parsed_response.get('cause', 'N/A')}\nEffect: {parsed_response.get('effect', 'N/A')}\nExplanation: {parsed_response.get('explanation', 'N/A')}")
        return True

    @requires_security
    @auto_save
    def _handle_estate_inventory(self) -> bool:
        """
            Handle viewing estate inventory in security room

                Returns:
                    bool: True if estate inventory was viewed successfully
        """
        self.agent.game_state.current_room.terminal.set_estate_inventory()  # type: ignore
        return True

    @requires_security
    @auto_save
    def _handle_security_level(self, context: str) -> bool:
        """
            Handle altering security level by having LLM decide

                Args:
                    context (str): Current game state context

                Returns:
                    bool: True if security level was altered successfully
        """
        response = self.agent.decide_security_level(context)
        parsed_response = parse_security_level_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"Security Level Response:\nLevel: {parsed_response['security_level']}\nExplanation: {parsed_response['explanation']}")
        self.agent.game_state.current_room.terminal.set_security_level(parsed_response.get("level", "MEDIUM"))  # type: ignore
        return True

    @requires_security
    @auto_save
    def _handle_mode(self, context: str) -> bool:
        """
            Handle altering security mode by having LLM decide

                Args:
                    context (str): Current game state context

                Returns:
                    bool: True if security mode was altered successfully
        """
        response = self.agent.decide_mode(context)
        parsed_response = parse_mode_response(response)
        parsed_response["context"] = context
        self.agent.decision_memory.add_decision(parsed_response)
        print(f"Mode Response:\nMode: {parsed_response['mode']}\nExplanation: {parsed_response['explanation']}")
        self.agent.game_state.current_room.terminal.set_mode(parsed_response.get("mode", "LOCKED"))  # type: ignore
        self.agent.game_state.house.update_security_doors()
        return True

    @requires_office
    @auto_save
    def _handle_payroll(self) -> bool:
        """
            Handle running payroll in office room

                Returns:
                    bool: True if payroll was run successfully
        """
        self.agent.game_state.current_room.terminal.payroll_ran = True  # type: ignore
        print("Payroll has been run.")
        return True

    @requires_office
    @auto_save
    def _handle_gold_spread(self) -> bool:
        """
            Handle spreading gold in estate from office room

                Returns:
                    bool: True if gold was spread successfully
        """
        self.agent.game_state.current_room.terminal.gold_spread = True  # type: ignore
        print("Gold has been spread in the estate.")
        return True

    @requires_shelter
    @auto_save
    def _handle_time_lock_safe(self) -> bool:
        """
            Handle time lock safe command in shelter room

                Returns:
                    bool: True if time lock safe was activated successfully
        """
        self.agent.game_state.current_room.terminal.time_lock_safe = True  # type: ignore
        print("Time lock safe has been activated.")
        return True