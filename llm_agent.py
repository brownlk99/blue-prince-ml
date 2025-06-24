import json
import re
import time
from typing import List, Optional, Union
import easyocr
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from nltk.corpus.reader import str2tuple
from game_state import GameState
from memory import NoteMemory, PreviousRunMemory, RoomMemory, TermMemory, DecisionMemory
from terminal import Terminal, SecurityTerminal, ShelterTerminal, OfficeTerminal, LabTerminal
from room import PuzzleRoom, Room, ShopRoom
from loguru import logger

class BluePrinceAgent:
    def __init__(self, game_state: Union[GameState, None] = None, verbose: bool = False):
        self.llm_o4_mini = ChatOpenAI(model="o4-mini")
        self.llm_gpt_4_1_nano = ChatOpenAI(model="gpt-4.1-nano")
        self.note_memory = NoteMemory()
        self.term_memory = TermMemory()
        self.room_memory = RoomMemory()
        self.previous_run_memory = PreviousRunMemory()
        self.decision_memory = DecisionMemory()
        self.game_state = game_state if game_state else GameState()
        self.previously_chosen_room = ""
        self.previously_chosen_door = ""
        self.verbose = verbose

    def _format_term_memory_section(self):
        if self.term_memory.terms:
            terms_section = "\nTERMS & DEFINITIONS:\n"
            for k, v in self.term_memory.terms.items():
                terms_section += f"{k}: {v}\n"
            return terms_section
        return ""
    
    def _format_room_memory_section(self):
        if self.room_memory.rooms:
            room_section = "The following section is a memory of rooms encountered in previous runs. These rooms are not necessarily present in the current house, but may help you make more informed decisions.\nROOM MEMORY:\n"
            for k, v in self.room_memory.rooms.items():
                room_section += f"{k}:\n"
                for attr, val in v.items():
                    room_section += f"  {attr}: {val}\n"
            return room_section
        return ""
    
    def _format_draft_summary(self, draft_options: List[Room]):
        summary = []
        for idx, room in enumerate(draft_options, 1):
            summary.append(
                f"{idx}. {room.name} (Cost: {room.cost}, Shape: {room.shape}, Rarity: {room.rarity})\n"
                f"   Doors: {', '.join([door.orientation for door in room.doors])}\n"
                f"   Description: {room.description}"
            )
            if room.additional_info:
                summary.append(f"   Additional Info: {room.additional_info}")
            summary.append("Remember, the COST associated with a room is the amount of GEMS you must spend to DRAFT it; if you do not have enough GEMS, you must choose a different room.")
        return "\n".join(summary)

    def _format_special_items(self):
        special_items = ["PRISM KEY", "SILVER KEY", "SECRET GARDEN KEY"]
        inventory = self.game_state.items
        found = False
        section = "The following item(s) can be used when opening doors (keep in mind some require you to be in specific areas of the HOUSE)"
        for special_item in special_items:
            if special_item in inventory.keys():
                section += f" -  {special_item}: {inventory[special_item]}\n"
                found = True
        if not found:
            return "None of the special items are currently in your inventory. Return 'NONE' for the special_item field.\n"
        return section       
    
    def _format_redraw_count(self) -> str:
        """
            Format the available redraw counts for the agent's actions.

                Args:
                    None

                Returns:
                    str: Formatted string of available redraws (empty if no redraws are available).
        """
        redraw_dict = self.game_state.get_available_redraws()
        redraw_text = "You may REDRAW the listed DRAFTS if you do not like the current options based upon the amount allotted below:\n"
        total_redraws = sum(redraw_dict.values())
        if total_redraws == 0:
            return "AVAILABLE REDRAWS: 0\n"
        if redraw_dict.get("dice", 0) > 0:
            redraw_text += f" - IVORY DICE: {redraw_dict['dice']} (each can be spent for a redraw at any time)\n"
        if redraw_dict.get("room", 0) > 0:
            redraw_text += f" - ROOM-BASED: {redraw_dict['room']} (these are free redraws granted by the current room and can only be used while DRAFTING IN THE CURRENT ROOM)\n"
        if redraw_dict.get("study", 0) > 0:
            redraw_text += f" - STUDY: {redraw_dict['study']} (due to the STUDY being within your current HOUSE, you may spend a GEM to REDRAW up to the number listed here)\n"
        return redraw_text + "\n"
    
    def _format_terminal_menu(self):
        """
            Format the terminal section for the agent's action decision.

                Args:
                    None

                Returns:
                    str: Formatted string of the current terminal's menu structure.
        """
        if self.game_state.current_room and self.game_state.current_room.terminal:
            menu_dict = self.game_state.current_room.terminal.get_menu_structure()
            section = f"You are at the {self.game_state.current_room.name} terminal. Do you wish to run any of the following commands?\n\n"
            for command, description in menu_dict:
                section += f" - {command}: {description}\n"
            return section
        return ""
    
    def _format_lab_experiment_section(self, options: dict[str, list[str]]):
        """
            Format the lab experiment options for the agent's action decision.

                Args:
                    options (dict): Dictionary of available experiments ('cause' and 'effect') with their details.

                Returns:
                    str: Formatted string of the available lab experiments.
        """
        section = "You are at the terminal in the LABORATORY. Choose any cause combination of cause and effect:\n"
        causes = options["cause"]
        effects = options["effect"]
        for cause in causes:
            section += f" - CAUSE: {cause}\n"
        for effect in effects:
            section += f" - EFFECT: {effect}\n"
        return section
    
    def _format_available_actions(self):
        """
        builds a list of available actions based on the current game state

            Returns:
                str: formatted string of available actions for the LLM prompt
    """
        flags = self.game_state.house.scan_rooms_for_available_actions()
        actions = []

        # always available
        actions.append('"explore": Decide that exploring is the best option; DO NOT choose a specific door or room yet, just decide if this is the action you wish to perform next.')
        # shop actions
        if flags["shop_room_present"]:
            actions.append('"peruse_shop": Use to see the list of items for sale in the current SHOP room.')
            actions.append('"purchase_item": You must be in a shop room to purchase.')
        # puzzle
        if flags["puzzle_room_present"]:
            actions.append('"solve_puzzle": You must be in the Parlor room to solve the puzzle.')
        if flags["secret_passage_present"]:
            actions.append('"open_secret_passage": You must be in the SECRET PASSAGE to perform this action.')
        # trunk
        if flags["trunk_present"]:
            actions.append('"open_trunk": You must be in the room with a trunk to open it AND have the necessary item/resource.')
        # dig
        if flags["dig_spot_present"]:
            actions.append('"dig": You must be in the room with a dig spot and have the necessary item to dig.')
        # terminal
        if flags["terminal_present"]:
            actions.append('"use_terminal": You must be in the room with a terminal to use it.')
        # coat check
        if flags["coat_check_present"]:
            actions.append('"store_item_in_coat_check": You must be in the Coat Check and have an item to store.')
            actions.append('"retrieve_item_from_coat_check": You must be in the Coat Check and have an item stored.')
        # utility closet check
        if flags["utility_closet_present"]:
            actions.append('"toggle_keycard_entry_switch": You must be in the Utility Closet to toggle the keycard entry switch.')
            actions.append('"toggle_gymnasium_switch": You must be in the Utility Closet to toggle the gymnasium switch.')
            actions.append('"toggle_darkroom_switch": You must be in the Utility Closet to toggle the darkroom switch.')
            actions.append('"toggle_garage_switch": You must be in the Utility Closet to toggle the garage switch.')
        # always available
        actions.append('"call_it_a_day": If you\'re out of possible moves but still have steps remaining you can call it a day to proceed to tomorrow.')
        # format as a string for the prompt
        return "AVAILABLE ACTIONS:\n" + "\n".join(f" - {a}" for a in actions) + "\n\n"

    def take_action(self, context: str) -> str:
        """
            Decide the next action for the agent based on the current GAME STATE and RELEVANT NOTES.

                Args:
                    None
                    
                Returns:
                    str: JSON string with the action to take.
        """
        notes = ""  #TODO: change this in the future
        terms_section = self._format_term_memory_section()
        rooms_section = self._format_room_memory_section()
        actions_section = self._format_available_actions()
        prompt = (f"GAME STATE:\n{context}\n"
            f"{terms_section}\n"
            f"{rooms_section}\n"
            f"RELEVANT NOTES:\n{notes}\n"
            "Based on the above context and notes, what action should the agent take?\n\n"
            f"{actions_section}"
            "If more information is needed to complete the action, return the high-level action and the parameters you know.\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "action": "ACTION NAME",\n'
            '  "explanation": "why this action is best given the current context, resources, and notes"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        else:
            print("LLM Taking Action: Deciding next action")
        return str(self.llm_o4_mini.invoke(messages).content)

    def parse_action_response(self, response: str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")

        action = data.get("action", "").strip()
        explanation = data.get("explanation", "").strip()

        return {"action": action, "explanation": explanation}

    def decide_door_to_explore(self, context: str) -> str:
        # notes = self.get_relevant_notes(query="Intro")
        notes = ""
        terms_section = self._format_term_memory_section()
        rooms_section = self._format_room_memory_section()
        special_items_section = self._format_special_items()
        prompt = (
            f"GAME STATE:\n{context}\n"
            f"{terms_section}\n"
            f"{rooms_section}\n"
            f"RELEVANT NOTES:\n{notes}\n\n"
            "Based on the above context and notes, what door should the player open?\n\n"
            "Choose a route that begins in the **current room** and ultimately leads to the **door you want to access within the TARGET ROOM of your choice** (TARGET ROOM **MUST** be a room that has currently been discovered and is currently accessible).\n"
            "If there is NOT a currently available path to the TARGET ROOM based upon the ROOMS currently in the HOUSE, you must choose a different option.\n"
            "Keep in mind that if a DOOR leads to a \"?\" then it is a valid option to choose to explore.\n"
            f"{special_items_section}"
            "Return **only** valid JSON in this exact shape:\n"
            '{\n'
            '  "target_room": "ROOM NAME",\n'
            '  "final_door":  "N|S|E|W",            # the door INSIDE target_room you intend to open\n'
            '  "path":        ["E","E","N","W"],    # list of directions you will take, to make it to the final door\n'
            '  "special_item": "ITEM NAME|NONE",    # the special item you will use to open the door (if any)\n'
            '  "explanation": "why this route is best given resources / notes"\n'
            '}\n\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
            "Make your decision based on available resources, relevant notes, and unexplored paths.\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        else:
            print("LLM Taking Action: Deciding door to explore")
        return str(self.llm_o4_mini.invoke(messages).content)
    
    def parse_door_exploration_response(self, response: str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")

        room_name = data.get("target_room", "").strip().upper()
        door_dir = data.get("final_door", "").strip().upper()[0]
        path = data.get("path", [])
        special_item = data.get("special_item", "NONE").strip().upper()
        explanation = data.get("explanation", "").strip()

        self.previously_chosen_room = room_name
        self.previously_chosen_door = door_dir

        return {
            "room": room_name,
            "door": door_dir,
            "path": path,
            "special_item": special_item,
            "explanation": explanation
        }
    
    def decide_purchase_item(self, context: str) -> str:
        """
            Decide which item to purchase based on the current GAME STATE and available items in the shop.
                
                Args:
                    None

                Returns:
                    str: JSON string with the item to purchase and quantity.
        """
        if self.game_state.current_room and isinstance(self.game_state.current_room, ShopRoom):
            items_for_sale = self.game_state.current_room.items_for_sale
        else:
            items_for_sale = {}
        if not items_for_sale:
            items_str = "No items are currently for sale in this shop, if the shop has not been perused yet, you must do so first."
        else:
            items_str = "\n".join(f"- {item}: {price}" for item, price in items_for_sale.items())
        terms_section = self._format_term_memory_section()
        prompt = (
            f"GAME STATE:\n{context}\n"
            f"{terms_section}\n"
            f"You are in a shop - {self.game_state.current_room.name if self.game_state.current_room else 'None'}.\n"
            f"Items currently for sale:\n{items_str}\n\n"
            "Which item (if any) do you wish to purchase, and how many?\n"
            "If you do not wish to purchase anything, return 'None' within the item field with a quantity of 0.\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "item": "ITEM NAME",\n'
            '  "quantity": NUMBER,\n'
            '  "explanation": "why this decision is the best in your opinion"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        else:
            print("LLM Taking Action: Deciding purchase item")
        return str(self.llm_o4_mini.invoke(messages).content)
    
    def parse_purchase_response(self, response: str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")

        item = data.get("item", "").strip().upper()
        quantity = data.get("quantity", 0)
        explanation = data.get("explanation", "").strip()

        return {
            "item": item,
            "quantity": quantity,
            "explanation": explanation
        }
    
    def decide_drafting_option(self, draft_options: List[Room], context: str) -> str:
        notes = ""
        draft_summary = self._format_draft_summary(draft_options)
        terms_section = self._format_term_memory_section()
        rooms_section = self._format_room_memory_section()
        redraw_section = self._format_redraw_count()
        prompt = (
            f"GAME STATE:\n{context}\n"
            f"{terms_section}\n"
            f"{rooms_section}\n"
            f"RELEVANT NOTES:\n{notes}\n\n"
            f"You are choosing between 3 rooms to draft through the {self.previously_chosen_room} {self.previously_chosen_door} door.\n"
            f"Drafting Options:\n{draft_summary}\n"
            f"{redraw_section}"
            f"Which should the player choose and why?\n"
            "If you do not like any of the available options, have REDRAWS available, and wish to draft new rooms, return only this JSON:\n"
            '{\n'
            '  "action": "REDRAW",\n'
            '  "type": "DICE|ROOM|STUDY",\n'
            '  "explanation": "why a redraw is preferred"\n'
            '}\n'
            "Otherwise, return only this JSON:\n"
            '{\n'
            '  "room": "ROOM NAME",\n'
            '  "explanation": "why this room is best given resources / notes",\n'
            '  "enter": "YES|NO"  # do you wish to enter the newly discovered room (in order to obtain a room\'s items you must enter)?\n'
            '}\n\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
            "Make your decision based on available resources, relevant notes, and unexplored paths.\n"
        )
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        else:
            print("LLM Taking Action: Deciding drafting option")
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]

        return str(self.llm_o4_mini.invoke(messages).content)
        
    def parse_drafting_response(self, response: str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")

        if data.get("action", "").strip().upper() == "REDRAW":
            return {
                "action": "REDRAW",
                "type": data.get("type", "").strip().upper(),
                "explanation": data.get("explanation", "").strip()
            }
        else:
            room_name = data.get("room", "").strip().upper()
            explanation = data.get("explanation", "").strip()
            enter = data.get("enter", "").strip().upper()
            return {
                "room": room_name,
                "explanation": explanation,
                "enter": enter
            }
    
    def solve_parlor_puzzle(self, reader: easyocr.Reader, context: str, editor_path: Optional[str] = None) -> str:
        if self.game_state.current_room and isinstance(self.game_state.current_room, PuzzleRoom):
            boxes = self.game_state.current_room.parlor_puzzle(reader, editor_path)
        else:
            boxes = {}
        terms_section = self._format_term_memory_section()
        prompt = (
            f"GAME STATE:\n{context}\n"
            f"{terms_section}\n"
            "Rules that NEVER change:\n"
            " • THERE WILL ALWAYS BE AT LEAST ONE BOX THAT DISPLAYS ONLY TRUE STATEMENTS.\n"
            " • THERE WILL ALWAYS BE AT LEAST ONE BOX WHICH DISPLAYS ONLY FALSE STATEMENTS\n"
            " • ONLY ONE BOX HAS A PRIZE WITHIN. THE OTHER 2 ARE ALWAYS EMPTY.\n\n"
            "The boxes from left to right are:\n"
            " - BLUE BOX\n"
            " - WHITE BOX\n"
            " - BLACK BOX\n\n"
            "Here are today's statements:\n"
            f"BLUE BOX:\n\"{boxes.get('BLUE', '')}\"\n\n"
            f"WHITE BOX:\n\"{boxes.get('WHITE', '')}\"\n\n"
            f"BLACK BOX:\n\"{boxes.get('BLACK', '')}\"\n\n"
            "State which box must contain the gems, and why.\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "box": "BOX COLOR",\n'
            '  "explanation": "why this box contains the gems"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n\n"
        )
        messages = [
            SystemMessage(content="You are a logician helping a Blue Prince player solve the Parlor three-boxes puzzle."),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        else:
            print("LLM Taking Action: Solving parlor puzzle")
        return str(self.llm_o4_mini.invoke(messages).content)
    
    def parse_parlor_response(self, response: str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")

        box = data.get("box", "").strip().upper()
        explanation = data.get("explanation", "").strip()

        return {
            "box": box,
            "explanation": explanation
        }

    def use_terminal(self, context: str) -> str:
        terms_section = self._format_term_memory_section()
        terminal_section = self._format_terminal_menu()
        prompt = (
            f"GAME STATE:\n{context}\n"
            f"{terms_section}\n"
            f"{terminal_section}\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "command": "COMMAND NAME",\n'
            '  "explanation": "why this command is best given the current context"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        else:
            print("LLM Taking Action: Using terminal")
        return str(self.llm_o4_mini.invoke(messages).content)
    
    def parse_terminal_response(self, response: str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")

        command = data.get("command", "").strip()
        explanation = data.get("explanation", "").strip()

        return {
            "command": command,
            "explanation": explanation
        }
    
    def decide_security_level(self, context: str) -> str:
        """
            Decide the security level for the estate based on the current GAME STATE and available security levels.

                Args:
                    None

                Returns:
                    str: JSON string with the chosen security level and explanation.
        """
        terms_section = self._format_term_memory_section()
        prompt = (
            f"GAME STATE:\n{context}\n"
            f"{terms_section}\n"
            "Based on the above context, what security level should be set for the estate?\n\n"
            "AVAILABLE SECURITY LEVELS:\n"
            " - LOW\n"
            " - MEDIUM\n"
            " - HIGH\n\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "security_level": "LOW|MEDIUM|HIGH",\n'
            '  "explanation": "why this security level is best given the current context"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        else:
            print("LLM Taking Action: Deciding security level")
        return str(self.llm_o4_mini.invoke(messages).content)

    def parse_security_level_response(self, response: str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")

        security_level = data.get("security_level", "").strip()
        explanation = data.get("explanation", "").strip()

        return {
            "security_level": security_level,
            "explanation": explanation
        }
    
    def decide_mode(self, context: str) -> str:
        """
            Decide the offline mode for security doors based on the current GAME STATE and available modes.

                Args:
                    None

                Returns:
                    str: JSON string with the chosen mode and explanation.
        """
        terms_section = self._format_term_memory_section()
        prompt = (
            f"GAME STATE:\n{context}\n"
            f"{terms_section}\n"
            "Based on the above context, what offline mode should be set for security doors?\n\n"
            "AVAILABLE MODES:\n"
            " - LOCKED\n"
            " - UNLOCKED\n\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "mode": "LOCKED|UNLOCKED",\n'
            '  "explanation": "why this mode is best given the current context"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        else:
            print("LLM Taking Action: Deciding mode")
        return str(self.llm_o4_mini.invoke(messages).content)
    
    def parse_mode_response(self, response: str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")

        mode = data.get("mode", "").strip()
        explanation = data.get("explanation", "").strip()

        return {
            "mode": mode,
            "explanation": explanation
        }

    def decide_lab_experiment(self, options: dict[str, list[str]], context: str) -> str:
        """
            Choose a lab experiment based on the current GAME STATE and available experiments.

                Args:
                    options (dict): Dictionary of available experiments ('cause' and 'effect') with their details.

                Returns:
                    str: JSON string with the chosen experiment and explanation.
        """
        terms_section = self._format_term_memory_section()
        lab_section = self._format_lab_experiment_section(options)
        prompt = (
            f"GAME STATE:\n{context}\n"
            f"{terms_section}\n"
            f"{lab_section}\n"
            "If you do not like any of the available options, return only this JSON:\n"
            '{\n'
            '  "action": "LOGIN TO NETWORK|EXIT",\n'
            '  "explanation": "why a you don\'t like the available options"\n'
            '}\n'
            "Otherwise, return only this JSON:\n"
            '{\n'
            '  "cause": "EXPERIMENT CAUSE",\n'
            '  "effect": "EXPERIMENT EFFECT",\n'
            '  "explanation": "why this experiment is best given the current context"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        else:
            print("LLM Taking Action: Deciding lab experiment")
        return str(self.llm_o4_mini.invoke(messages).content)
    
    def parse_lab_experiment_response(self, response: str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")

        if data.get("action", ""):
            action = data.get("action", "").strip().upper()
            explanation = data.get("explanation", "").strip()
            return {
                "action": action,
                "explanation": explanation
            }
        else:
            cause = data.get("cause", "").strip()
            effect = data.get("effect", "").strip()
            explanation = data.get("explanation", "").strip()
            return {
                "cause": cause,
                "effect": effect,
                "explanation": explanation
            }
        
    # def shelter_decide_time_lock_safe(self):
    #     """
    #         Decide the time to lock the safe in the shelter based on the current GAME STATE.

    #             Args:
    #                 None

    #             Returns:
    #                 str: JSON string with the chosen time and explanation.
    #     """
    #     context = self.game_state.summarize_for_llm()
    #     terms_section = self._format_term_memory_section()
    #     prompt = (
    #         f"GAME STATE:\n{context}\n"
    #         f"{terms_section}\n"
    #         "Based on the above context, what time should the safe in the shelter be locked?\n\n"
    #         "AVAI

    def coat_check_prompt(self, action: str, context: str) -> str:
        """
            Decide whether to store or retrieve an item from the coat check based on the current GAME STATE.

                Args:
                    None

                Returns:
                    str: JSON string with the chosen action and explanation.
        """
        notes = ""
        terms_section = self._format_term_memory_section()
        rooms_section = self._format_room_memory_section()
        prompt = (
            f"GAME STATE:\n{context}\n"
            f"{terms_section}\n"
            f"{rooms_section}\n"
            f"RELEVANT NOTES:\n{notes}\n\n"
            f"Based on the above context, what item do you wish to {action}? (Choose 'None' if you no longer wish to {action} an item)\n\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "item": "ITEM NAME",\n'
            '  "explanation": "EXPLANATION"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        else:
            print(f"LLM Taking Action: Coat check {action.lower()}")
        return str(self.llm_o4_mini.invoke(messages).content)
    
    def parse_coat_check_response(self, response: str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")

        item = data.get("item", "").strip()
        explanation = data.get("explanation", "").strip()

        return {
            "item": item,
            "explanation": explanation
        }
    
    def open_secret_passage(self, context: str) -> str:
        """
            Decide whether to open the secret passage based on the current GAME STATE.

                Args:
                    None

                Returns:
                    str: JSON string with the decision to open the secret passage and explanation.
        """
        terms_section = self._format_term_memory_section()
        rooms_section = self._format_room_memory_section()
        #TODO: add more context here
        prompt = (
            f"GAME STATE:\n{context}\n"
            f"{terms_section}\n"
            f"{rooms_section}\n"
            "Based on the above context, what TYPE of ROOM would you like to open the SECRET PASSAGE to?\n\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "room_type": RED|GREEN|ORANGE|YELLOW|PURPLE,\n'
            '  "explanation": "why this decision is best given the current context"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        else:
            print("LLM Taking Action: Deciding secret passage")
        return str(self.llm_o4_mini.invoke(messages).content)

    def parse_secret_passage_response(self, response: str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")

        room_type = data.get("room_type", "").strip().upper()
        explanation = data.get("explanation", "").strip()

        return {
            "room_type": room_type,
            "explanation": explanation
        }

    def get_relevant_notes(self, query: str, k: int = 3) -> str:
        relevant = self.note_memory.search(query, k=k)
        if not relevant:
            return "No RELEVANT NOTES found."
        return "\n".join(f"- {doc.page_content}" for doc in relevant)
    
    def generate_note_title(self, note_content: str) -> str:
        """
        Generate a title for the note based on its content.
        This is a simple heuristic and can be improved with more complex logic.
        """
        prompt = (f"Give the following note a short descriptive title (no more than four words at most):\n\n{note_content}"
                  "\n\n Return only valid JSON in this exact shape:\n"
                  '{\n'
                  '  "title": "NOTE TITLE"\n'
                  '}\n'
                  "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n\n"
        )
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=prompt)
        ]
        return str(self.llm_gpt_4_1_nano.invoke(messages).content)
    
    def parse_note_title_response(self, response: str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")

        title = data.get("title", "").strip()

        return title

    def manual_llm_follow_up(self) -> str:
        if not self.decision_memory.decisions:
            return "No previous decisions to follow up on."

        most_recent_decision = self.decision_memory.decisions[-1].copy()
        most_recent_context = most_recent_decision['context']
        most_recent_decision.pop("context", None)           # remove context from decision
        terms_section = self._format_term_memory_section()
        rooms_section = self._format_room_memory_section()
        input_section = input("Please enter any additional specific questions that may be relevant to the previous LLM decision: ")
        notes = ""
        prompt = (f"GAME STATE:\n{most_recent_context}\n"
            f"{terms_section}\n"
            f"{rooms_section}\n"
            f"RELEVANT NOTES:\n{notes}\n"
            f"Previous Response:\n{most_recent_decision}\n\n"
            f"Based on the above context, what is the most likely reason for the previous LLM decision? {input_section}"
        )
        messages = [
            SystemMessage(content="You are an expert at deduction and you're trying to reason why the previous LLM decision could have been made."),
            HumanMessage(content=prompt)
        ]

        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        else:
            print("LLM Taking Action: Analyzing previous decision")

        return str(self.llm_o4_mini.invoke(messages).content)