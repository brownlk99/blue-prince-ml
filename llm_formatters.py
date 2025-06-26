from typing import List
from room import Room


def format_term_memory_section(term_memory):
    """Format the term memory section for LLM prompts"""
    if term_memory.terms:
        terms_section = "\nTERMS & DEFINITIONS:\n"
        for k, v in term_memory.terms.items():
            terms_section += f"{k}: {v}\n"
        return terms_section
    return ""


def format_room_memory_section(room_memory):
    """Format the room memory section for LLM prompts"""
    if room_memory.rooms:
        room_section = "The following section is a memory of rooms encountered in previous runs. These rooms are not necessarily present in the current house, but may help you make more informed decisions.\nROOM MEMORY:\n"
        for k, v in room_memory.rooms.items():
            room_section += f"{k}:\n"
            for attr, val in v.items():
                room_section += f"  {attr}: {val}\n"
        return room_section
    return ""


def format_draft_summary(draft_options: List[Room]):
    """Format the draft summary for LLM prompts"""
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


def format_special_items(game_state):
    """Format the special items section for LLM prompts"""
    special_items = ["PRISM KEY", "SILVER KEY", "SECRET GARDEN KEY"]
    inventory = game_state.items
    found = False
    section = "The following item(s) can be used when opening doors (keep in mind some require you to be in specific areas of the HOUSE)"
    for special_item in special_items:
        if special_item in inventory.keys():
            section += f" -  {special_item}: {inventory[special_item]}\n"
            found = True
    if not found:
        return "None of the special items are currently in your inventory. Return 'NONE' for the special_item field.\n"
    return section


def format_redraw_count(game_state) -> str:
    """
    Format the available redraw counts for the agent's actions.

    Args:
        game_state: The current game state

    Returns:
        str: Formatted string of available redraws (empty if no redraws are available).
    """
    redraw_dict = game_state.get_available_redraws()
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


def format_terminal_menu(game_state):
    """
    Format the terminal section for the agent's action decision.

    Args:
        game_state: The current game state

    Returns:
        str: Formatted string of the current terminal's menu structure.
    """
    if game_state.current_room and game_state.current_room.terminal:
        menu_dict = game_state.current_room.terminal.get_menu_structure()
        section = f"You are at the {game_state.current_room.name} terminal. Do you wish to run any of the following commands?\n\n"
        for command, description in menu_dict:
            section += f" - {command}: {description}\n"
        return section
    return ""


def format_lab_experiment_section(options: dict[str, list[str]]):
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


def format_available_actions(game_state):
    """
    Builds a list of available actions based on the current game state

    Args:
        game_state: The current game state

    Returns:
        str: formatted string of available actions for the LLM prompt
    """
    flags = game_state.house.scan_rooms_for_available_actions()
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