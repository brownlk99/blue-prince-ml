from typing import List, Optional, Union

import easyocr

from game.game_state import GameState
from game.memory import NoteMemory, PreviousRunMemory, RoomMemory, TermMemory, DecisionMemory
from game.room import Room, PuzzleRoom, CoatCheck
from .llm_client import LLMClient, _context_window
from .llm_formatters import (
    format_term_memory_section,
    format_room_memory_section,
    format_draft_summary,
    format_special_items,
    format_redraw_count,
    format_terminal_menu,
    format_lab_experiment_section,
    format_available_actions,
    format_move_context,
    format_shop_items
)
from utils import thinking_animation


# System prompt constants - all game-specific prompts defined here
SYSTEM_EXPLORER = "You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"
SYSTEM_LOGICIAN = "You are a logician helping a Blue Prince player solve the Parlor three-boxes puzzle."
SYSTEM_ASSISTANT = "You are a helpful assistant."
SYSTEM_DEDUCTION = "You are an expert at deduction and you're trying to reason why the previous LLM decision could have been made."

class BluePrinceAgent:
    def __init__(self, game_state: Union[GameState, None] = None, verbose: bool = False, model_name: str = "openai:gpt-4o-mini", use_utility_model: bool = False):
        self.llm_client = LLMClient(model_name)
        self.note_memory = NoteMemory()
        self.term_memory = TermMemory()
        self.room_memory = RoomMemory()
        self.previous_run_memory = PreviousRunMemory()
        self.decision_memory = DecisionMemory()
        self.game_state = game_state if game_state else GameState()
        self.previously_chosen_room = ""
        self.previously_chosen_door = ""
        self.verbose = verbose

        if use_utility_model:
            self.utility_client = LLMClient(self.llm_client._get_default_utility_model())
        else:
            self.utility_client = None

    def _invoke(self, system_message: str, user_message: str, use_utility_model: bool = False) -> str:
        """Invoke the LLM and handle usage tracking"""
        client = self.utility_client if (use_utility_model and self.utility_client) else self.llm_client
        response, usage = client.chat(system_message, user_message)
        
        # Print usage statistics
        ctx_limit = _context_window(client.model_name)
        pct = f"{usage.input_tokens/ctx_limit:.1%}" if ctx_limit else "?"
        
        print(f"[TOKENS] prompt={usage.input_tokens}  completion={usage.output_tokens}  "
              f"total={usage.total_tokens}/{ctx_limit}  ({pct} of window)")
        
        return response

    def _build_prompt(self, context: str, additional_sections: Optional[dict] = None, 
                     include_terms: bool = True, include_rooms: bool = True, 
                     include_notes: bool = True) -> str:
        """
        Build a standardized user prompt with common sections
        
        Args:
            context: Game state context
            additional_sections: Dict of additional sections to include {section_name: content}
            include_terms: Whether to include terms section
            include_rooms: Whether to include rooms section  
            include_notes: Whether to include notes section
            
        Returns:
            str: Formatted prompt sections
        """
        sections = [f"GAME STATE:\n{context}"]
        
        if include_terms:
            terms_section = format_term_memory_section(self.term_memory)
            if terms_section:
                sections.append(terms_section)
        
        if include_rooms:
            rooms_section = format_room_memory_section(self.room_memory)
            if rooms_section:
                sections.append(rooms_section)
        
        if include_notes:
            notes = ""  # TODO: change this in the future
            sections.append(f"RELEVANT NOTES:\n{notes}")
        
        if additional_sections:
            for section_name, content in additional_sections.items():
                if content:
                    sections.append(content)
        
        return "\n".join(sections) + "\n"

    def take_action(self, context: str) -> str:
        """
            Decide the next action for the agent based on the current GAME STATE and RELEVANT NOTES.

                Args:
                    None
                    
                Returns:
                    str: JSON string with the action to take.
        """
        additional_sections = {
            "move_context": format_move_context(self.decision_memory.get_move_context()),
            "actions": format_available_actions(self.game_state)
        }
        
        prompt_base = self._build_prompt(context, additional_sections)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
            "Based on the above context and notes, what action should the agent take?\n\n"
            "If more information is needed to complete the action, return the high-level action and the parameters you know.\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "action": "ACTION NAME",\n'
            '  "explanation": "why this action is best given the current context, resources, and notes"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding next action"):
            response = self._invoke(system_message, user_message)
        return response

    def decide_move(self, context: str) -> str:
        """
            Decide where to move and what action to take there.

                Args:
                    context: Current game state context
                    
                Returns:
                    str: JSON string with the move decision.
        """
        prompt_base = self._build_prompt(context)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
            "Based on the above context and notes, where should you move and what action do you plan to take there?\n\n"
            "Choose a route that begins in the **current room** and leads to your **target room** (TARGET ROOM **MUST** be a room that has currently been discovered and is currently accessible).\n"
            "If there is NOT a currently available path to the TARGET ROOM based upon the ROOMS currently in the HOUSE, you must choose a different option.\n"
            "Return **only** valid JSON in this exact shape:\n"
            '{\n'
            '  "target_room": "ROOM NAME",\n'
            '  "path": ["E","E","N","W"],    # list of directions you will take to reach the target room\n'
            '  "planned_action": "ACTION",  # the action you plan to take once you reach the target room\n'
            '  "explanation": "why this route is best given resources / notes"\n'
            '}\n\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
            "Make your decision based on available resources, relevant notes, and unexplored paths.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding move"):
            response = self._invoke(system_message, user_message)
        return response

    def decide_door_to_open(self, context: str) -> str:
        """
            Decide which door in the current room to open.

                Args:
                    context: Current game state context
                    
                Returns:
                    str: JSON string with the door opening decision.
        """
        additional_sections = {
            "special_items": format_special_items(self.game_state)
        }
        
        prompt_base = self._build_prompt(context, additional_sections)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
            "Based on the above context and notes, which door in the current room do you wish to open?\n\n"
            "Choose a door direction (N, S, E, W) that is available in your current room.\n"
            "Keep in mind that if a DOOR leads to a \"?\" then it is a valid option to choose to explore / open.\n"
            "Return **only** valid JSON in this exact shape:\n"
            '{\n'
            '  "door_direction": "N|S|E|W",\n'
            '  "special_item": "ITEM NAME|NONE",    # the special item you will use to open the door (if any)\n'
            '  "explanation": "why this door is best given resources / notes"\n'
            '}\n\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
            "Make your decision based on available resources, relevant notes, and unexplored paths.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding door to open"):
            response = self._invoke(system_message, user_message)
        return response

    def decide_purchase_item(self, context: str) -> str:
        """
            Decide which item to purchase based on the current GAME STATE and available items in the shop.
                
                Args:
                    None

                Returns:
                    str: JSON string with the item to purchase and quantity.
        """
        additional_sections = {
            "shop_items": format_shop_items(self.game_state)
        }
        
        prompt_base = self._build_prompt(context, additional_sections, include_rooms=False, include_notes=False)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
            "Which item (if any) do you wish to purchase, and how many?\n"
            "If you do not wish to purchase anything, return 'None' within the item field with a quantity of 0.\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "item": "ITEM NAME",\n'
            '  "quantity": NUMBER,\n'
            '  "explanation": "why this decision is the best in your opinion"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding purchase item"):
            response = self._invoke(system_message, user_message)
        return response

    def decide_drafting_option(self, draft_options: List[Room], context: str) -> str:
        additional_sections = {
            "draft_options": f"You are choosing between 3 rooms to draft through the {self.previously_chosen_room} {self.previously_chosen_door} door.\nDrafting Options:\n{format_draft_summary(draft_options)}",
            "redraw_section": format_redraw_count(self.game_state)
        }
        
        prompt_base = self._build_prompt(context, additional_sections)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
            "Which should the player choose and why?\n"
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
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding drafting option"):
            response = self._invoke(system_message, user_message)
        return response

    def solve_parlor_puzzle(self, reader: easyocr.Reader, context: str, editor_path: Optional[str] = None) -> str:
        if self.game_state.current_room and isinstance(self.game_state.current_room, PuzzleRoom):
            boxes = self.game_state.current_room.parlor_puzzle(reader, editor_path)
        else:
            boxes = {}
        
        additional_sections = {
            "puzzle_info": (
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
                f"BLACK BOX:\n\"{boxes.get('BLACK', '')}\""
            )
        }
        
        prompt_base = self._build_prompt(context, additional_sections, include_rooms=False, include_notes=False)
        
        system_message = SYSTEM_LOGICIAN
        user_message = (prompt_base +
            "State which box must contain the gems, and why.\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "box": "BOX COLOR",\n'
            '  "explanation": "why this box contains the gems"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Solving parlor puzzle"):
            response = self._invoke(system_message, user_message)
        return response

    def use_terminal(self, context: str) -> str:
        additional_sections = {
            "terminal_menu": format_terminal_menu(self.game_state)
        }
        
        prompt_base = self._build_prompt(context, additional_sections, include_rooms=False, include_notes=False)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "command": "COMMAND NAME",\n'
            '  "explanation": "why this command is best given the current context"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Using terminal"):
            response = self._invoke(system_message, user_message)
        return response

    def guess_network_password(self, context: str) -> str:
        """
        Have the LLM attempt to guess the network password based on context and notes.
        
        Args:
            context: Current game state context
            
        Returns:
            str: JSON string with the password guess and reasoning
        """
        prompt_base = self._build_prompt(context)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
            "You need to guess the password to access the network.\n"
            "Based on your notes, game context, and any clues you've discovered, what password would you try?\n\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "password": "YOUR GUESS",\n'
            '  "explanation": "why you think this might be the password based on clues or context"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Guessing network password"):
            response = self._invoke(system_message, user_message)
        return response

    def decide_special_order(self, available_items: List[str], context: str) -> str:
        """
        Decide which special order item to request from the commissary.
        
        Args:
            available_items: List of items available for special order
            context: Current game state context
            
        Returns:
            str: JSON string with the special order decision
        """
        items_list = "\n".join([f" - {item}" for item in available_items])
        
        additional_sections = {
            "special_order_info": f"AVAILABLE SPECIAL ORDER ITEMS:\n{items_list}\n\nSpecial orders take 1-3 days to arrive at the COMMISSARY."
        }
        
        prompt_base = self._build_prompt(context, additional_sections, include_rooms=False, include_notes=False)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
            "Based on the above context, which special order item (if any) would you want to order?\n\n"
            "If you don't want to order anything, return 'NONE' as the item.\n\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "item": "ITEM NAME|NONE",\n'
            '  "explanation": "why this item would be useful or why you chose not to order"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding special order"):
            response = self._invoke(system_message, user_message)
        return response

    def decide_security_level(self, context: str) -> str:
        """
            Decide the security level for the estate based on the current GAME STATE and available security levels.

                Args:
                    None

                Returns:
                    str: JSON string with the chosen security level and explanation.
        """
        prompt_base = self._build_prompt(context, include_rooms=False, include_notes=False)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
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
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding security level"):
            response = self._invoke(system_message, user_message)
        return response

    def decide_mode(self, context: str) -> str:
        """
            Decide the offline mode for security doors based on the current GAME STATE and available modes.

                Args:
                    None

                Returns:
                    str: JSON string with the chosen mode and explanation.
        """
        prompt_base = self._build_prompt(context, include_rooms=False, include_notes=False)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
            "Based on the above context, what offline mode should be set for security doors?\n\n"
            "AVAILABLE MODES:\n"
            " - LOCKED\n"
            " - UNLOCKED\n\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "mode": "LOCKED|UNLOCKED",\n'
            '  "explanation": "why this mode is best given the current context"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding mode"):
            response = self._invoke(system_message, user_message)
        return response

    def decide_lab_experiment(self, options: dict[str, list[str]], context: str) -> str:
        """
            Choose a lab experiment based on the current GAME STATE and available experiments.

                Args:
                    options (dict): Dictionary of available experiments ('cause' and 'effect') with their details.

                Returns:
                    str: JSON string with the chosen experiment and explanation.
        """
        additional_sections = {
            "lab_experiments": format_lab_experiment_section(options)
        }
        
        prompt_base = self._build_prompt(context, additional_sections, include_rooms=False, include_notes=False)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
            "If you do not like any of the available options, return only this JSON:\n"
            '{\n'
            '  "action": "EXIT",\n'
            '  "explanation": "why a you don\'t like the available options"\n'
            '}\n'
            "If you wish to pause/clear the current experiment, return only this JSON:\n"
            '{\n'
            '  "action": "PAUSE EXPERIMENT",\n'
            '  "explanation": "why you want to pause the current experiment"\n'
            '}\n'
            "Otherwise, return only this JSON:\n"
            '{\n'
            '  "cause": "EXPERIMENT CAUSE",\n'
            '  "effect": "EXPERIMENT EFFECT",\n'
            '  "explanation": "why this experiment is best given the current context"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding lab experiment"):
            response = self._invoke(system_message, user_message)
        return response

    def coat_check_prompt(self, action: str, context: str) -> str:
        """
            Decide whether to store or retrieve an item from the coat check based on the current GAME STATE.

                Args:
                    action: The action to perform (store/retrieve)
                    context: Current game state context

                Returns:
                    str: JSON string with the chosen action and explanation.
        """
        additional_sections = {
            "action_prompt": f"Based on the above context, what item do you wish to {action}? (Choose 'None' if you no longer wish to {action} an item)"
        }
        
        prompt_base = self._build_prompt(context, additional_sections)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "item": "ITEM NAME",\n'
            '  "explanation": "EXPLANATION"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation(f"LLM Taking Action: Coat check {action.lower()}"):
            response = self._invoke(system_message, user_message)
        return response

    def open_secret_passage(self, context: str) -> str:
        """
            Decide whether to open the secret passage based on the current GAME STATE.

                Args:
                    context: Current game state context

                Returns:
                    str: JSON string with the decision to open the secret passage and explanation.
        """
        # TODO: add more context here
        prompt_base = self._build_prompt(context, include_notes=False)
        
        system_message = SYSTEM_EXPLORER
        user_message = (prompt_base +
            "Based on the above context, what TYPE of ROOM would you like to open the SECRET PASSAGE to?\n\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "room_type": RED|GREEN|ORANGE|YELLOW|PURPLE,\n'
            '  "explanation": "why this decision is best given the current context"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        
        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding secret passage"):
            response = self._invoke(system_message, user_message)
        return response
    
    def generate_note_title(self, note_content: str) -> str:
        """
        Generate a title for the note based on its content.
        This is a simple heuristic and can be improved with more complex logic.
        """
        system_message = SYSTEM_ASSISTANT
        user_message = (f"Give the following note a short descriptive title (no more than four words at most):\n\n{note_content}"
                  "\n\n Return only valid JSON in this exact shape:\n"
                  '{\n'
                  '  "title": "NOTE TITLE"\n'
                  '}\n'
                  "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        
        response = self._invoke(system_message, user_message, use_utility_model=True)
        return response

    def manual_llm_follow_up(self) -> str:
        if not self.decision_memory.decisions:
            return "No previous decisions to follow up on."

        most_recent_decision = self.decision_memory.decisions[-1].copy()
        most_recent_context = most_recent_decision['context']
        most_recent_decision.pop("context", None)           # remove context from decision
        input_section = input("Please enter any additional specific questions that may be relevant to the previous LLM decision: ")
        
        additional_sections = {
            "previous_response": f"Previous Response:\n{most_recent_decision}",
            "additional_question": f"Based on the above context, what is the most likely reason for the previous LLM decision? {input_section}"
        }
        
        prompt_base = self._build_prompt(most_recent_context, additional_sections)
        
        system_message = SYSTEM_DEDUCTION
        user_message = prompt_base

        if self.verbose:
            print("\nPrompt for LLM:\n" + user_message)
        print("\n")
        with thinking_animation("LLM Taking Action: Analyzing previous decision"):
            response = self._invoke(system_message, user_message)
        return response