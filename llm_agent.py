import json
import re
import time
from typing import List, Optional, Union, cast
import easyocr
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models import init_chat_model
from langchain_core.callbacks import get_usage_metadata_callback
from game_state import GameState
from memory import NoteMemory, PreviousRunMemory, RoomMemory, TermMemory, DecisionMemory
from terminal import Terminal, SecurityTerminal, ShelterTerminal, OfficeTerminal, LabTerminal
from room import PuzzleRoom, Room, ShopRoom
from langchain_openai import ChatOpenAI          # OpenAI family
from langchain_google_genai import ChatGoogleGenerativeAI  # Gemini family
from langchain_anthropic import ChatAnthropic    # Claude family
from langchain_google_vertexai import ChatVertexAI

from utils import thinking_animation
from llm_formatters import (
    format_term_memory_section,
    format_room_memory_section,
    format_draft_summary,
    format_special_items,
    format_redraw_count,
    format_terminal_menu,
    format_lab_experiment_section,
    format_available_actions
)

def _get_context_window(model_name: str) -> int:
    """
    Ask the vendor SDK for the model’s max-context window.
    Handles OpenAI, Anthropic, and both Google SDKs.
    Falls back to 0 if the field is absent or the call fails.
    """
    # Strip "provider:" prefix that init_chat_model sometimes adds,
    # e.g. "openai:o4-mini" → "o4-mini".
    if ":" in model_name:
        _, model_name = model_name.split(":", 1)

    try:
        # ---- OpenAI --------------------------------------------------
        if model_name.startswith(("gpt", "o")):                        # :contentReference[oaicite:0]{index=0}
            from openai import OpenAI
            info = OpenAI().models.retrieve(model_name)                # :contentReference[oaicite:1]{index=1}
            return cast(int, getattr(info, "context_window", 0))       # field exists at runtime

        # ---- Anthropic ----------------------------------------------
        if model_name.startswith(("claude", "anthropic")):             # :contentReference[oaicite:2]{index=2}
            import anthropic
            info = anthropic.Anthropic().models.retrieve(model_name)
            return cast(int, getattr(info, "context_length", 0))       # SDK returns ModelInfo

        # ---- Gemini / Google ----------------------------------------
        if model_name.lower().startswith(("gemini", "gai", "google")):
            try:
                # New SDK (recommended after Aug-2025)                 # :contentReference[oaicite:3]{index=3}
                from google.genai import GenerativeModel               # type: ignore
            except ModuleNotFoundError:
                # Legacy SDK (sunsets Aug-2025)                        # :contentReference[oaicite:4]{index=4}
                from google.generativeai.generative_models import GenerativeModel
            info = GenerativeModel(model_name)
            return cast(int, getattr(info, "input_token_limit", 0))    # public property
    except Exception:
        pass

    return 0          # offline, wrong ID, or unsupported provider

class BluePrinceAgent:
    def __init__(self, game_state: Union[GameState, None] = None, verbose: bool = False, model_name: str = "openai:o4-mini"):
        # self.model = init_chat_model(model_name)
        self.model = ChatVertexAI(model="gemini-2.5-pro")
        self.note_memory = NoteMemory()
        self.term_memory = TermMemory()
        self.room_memory = RoomMemory()
        self.previous_run_memory = PreviousRunMemory()
        self.decision_memory = DecisionMemory()
        self.game_state = game_state if game_state else GameState()
        self.previously_chosen_room = ""
        self.previously_chosen_door = ""
        self.verbose = verbose
        print(f"Using model: {self.model}")
        print(f"Model type: {type(self.model)}")
    def _invoke(self, messages):
        with get_usage_metadata_callback() as tracker:                     # universal handler
            response = self.model.invoke(messages, config={"callbacks": [tracker]})

        usage = next(iter(tracker.usage_metadata.values()), {})
        prompt = usage.get("input_tokens", 0)
        comp  = usage.get("output_tokens", 0)
        total = usage.get("total_tokens", prompt + comp)

        name = getattr(self.model, "model_name", getattr(self.model, "model", "?"))
        ctx = _get_context_window(name) or "?"
        pct = f"{prompt/ctx:.1%}" if isinstance(ctx, int) and ctx else "?"

        print(f"[TOKENS] prompt={prompt}  completion={comp}  "
            f"total={total}/{ctx}  ({pct} of window)")
        return response

    def take_action(self, context: str) -> str:
        """
            Decide the next action for the agent based on the current GAME STATE and RELEVANT NOTES.

                Args:
                    None
                    
                Returns:
                    str: JSON string with the action to take.
        """
        notes = ""  #TODO: change this in the future
        terms_section = format_term_memory_section(self.term_memory)
        rooms_section = format_room_memory_section(self.room_memory)
        actions_section = format_available_actions(self.game_state)
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
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding next action"):
            response = self._invoke(messages)
        return str(response.content)

    def decide_door_to_explore(self, context: str) -> str:
        # notes = self.get_relevant_notes(query="Intro")
        notes = ""
        terms_section = format_term_memory_section(self.term_memory)
        rooms_section = format_room_memory_section(self.room_memory)
        special_items_section = format_special_items(self.game_state)
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
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding door to explore"):
            response = self._invoke(messages)
        return str(response.content)

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
        terms_section = format_term_memory_section(self.term_memory)
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
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding purchase item"):
            response = self._invoke(messages)
        return str(response.content)

    def decide_drafting_option(self, draft_options: List[Room], context: str) -> str:
        notes = ""
        draft_summary = format_draft_summary(draft_options)
        terms_section = format_term_memory_section(self.term_memory)
        rooms_section = format_room_memory_section(self.room_memory)
        redraw_section = format_redraw_count(self.game_state)
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

        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding drafting option"):
            response = self._invoke(messages)
        return str(response.content)

    def solve_parlor_puzzle(self, reader: easyocr.Reader, context: str, editor_path: Optional[str] = None) -> str:
        if self.game_state.current_room and isinstance(self.game_state.current_room, PuzzleRoom):
            boxes = self.game_state.current_room.parlor_puzzle(reader, editor_path)
        else:
            boxes = {}
        terms_section = format_term_memory_section(self.term_memory)
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
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        messages = [
            SystemMessage(content="You are a logician helping a Blue Prince player solve the Parlor three-boxes puzzle."),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        print("\n")
        with thinking_animation("LLM Taking Action: Solving parlor puzzle"):
            response = self._invoke(messages)
        return str(response.content)

    def use_terminal(self, context: str) -> str:
        terms_section = format_term_memory_section(self.term_memory)
        terminal_section = format_terminal_menu(self.game_state)
        prompt = (
            f"GAME STATE:\n{context}\n"
            f"{terms_section}\n"
            f"{terminal_section}\n"
            "Return only valid JSON in this exact shape:\n"
            '{\n'
            '  "command": "COMMAND NAME",\n'
            '  "explanation": "why this command is best given the current context"\n'
            '}\n'
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        print("\n")
        with thinking_animation("LLM Taking Action: Using terminal"):
            response = self._invoke(messages)
        return str(response.content)

    def decide_security_level(self, context: str) -> str:
        """
            Decide the security level for the estate based on the current GAME STATE and available security levels.

                Args:
                    None

                Returns:
                    str: JSON string with the chosen security level and explanation.
        """
        terms_section = format_term_memory_section(self.term_memory)
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
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding security level"):
            response = self._invoke(messages)
        return str(response.content)

    def decide_mode(self, context: str) -> str:
        """
            Decide the offline mode for security doors based on the current GAME STATE and available modes.

                Args:
                    None

                Returns:
                    str: JSON string with the chosen mode and explanation.
        """
        terms_section = format_term_memory_section(self.term_memory)
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
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding mode"):
            response = self._invoke(messages)
        return str(response.content)

    def decide_lab_experiment(self, options: dict[str, list[str]], context: str) -> str:
        """
            Choose a lab experiment based on the current GAME STATE and available experiments.

                Args:
                    options (dict): Dictionary of available experiments ('cause' and 'effect') with their details.

                Returns:
                    str: JSON string with the chosen experiment and explanation.
        """
        terms_section = format_term_memory_section(self.term_memory)
        lab_section = format_lab_experiment_section(options)
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
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding lab experiment"):
            response = self._invoke(messages)
        return str(response.content)

    def coat_check_prompt(self, action: str, context: str) -> str:
        """
            Decide whether to store or retrieve an item from the coat check based on the current GAME STATE.

                Args:
                    None

                Returns:
                    str: JSON string with the chosen action and explanation.
        """
        notes = ""
        terms_section = format_term_memory_section(self.term_memory)
        rooms_section = format_room_memory_section(self.room_memory)
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
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        print("\n")
        with thinking_animation(f"LLM Taking Action: Coat check {action.lower()}"):
            response = self._invoke(messages)
        return str(response.content)

    def open_secret_passage(self, context: str) -> str:
        """
            Decide whether to open the secret passage based on the current GAME STATE.

                Args:
                    None

                Returns:
                    str: JSON string with the decision to open the secret passage and explanation.
        """
        terms_section = format_term_memory_section(self.term_memory)
        rooms_section = format_room_memory_section(self.room_memory)
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
            "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        messages = [
            SystemMessage(content="You are an expert explorer in the game Blue Prince and your goal is to make it to the Antechamber... it may be more difficult than you think!"),
            HumanMessage(content=prompt)
        ]
        if self.verbose:
            print("\nPrompt for LLM:\n" + prompt)
        print("\n")
        with thinking_animation("LLM Taking Action: Deciding secret passage"):
            response = self._invoke(messages)
        return str(response.content)
    
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
                  "Do NOT include any markdown or code block formatting (no triple backticks). Return ONLY the raw JSON object.\n"
        )
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=prompt)
        ]
        response = self._invoke(messages)
        return str(response.content)

    def manual_llm_follow_up(self) -> str:
        if not self.decision_memory.decisions:
            return "No previous decisions to follow up on."

        most_recent_decision = self.decision_memory.decisions[-1].copy()
        most_recent_context = most_recent_decision['context']
        most_recent_decision.pop("context", None)           # remove context from decision
        terms_section = format_term_memory_section(self.term_memory)
        rooms_section = format_room_memory_section(self.room_memory)
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
        print("\n")
        with thinking_animation("LLM Taking Action: Analyzing previous decision"):
            response = self._invoke(messages)
        return str(response.content)