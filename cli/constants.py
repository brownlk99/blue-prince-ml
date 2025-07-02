"""
Constants for CLI interface.
"""

# File paths
CURRENT_RUN_FILE = './jsons/current_run.json'

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
    '13': ('save_game_state', 'Save Game State - Save the current game state to a JSON file.'),
    '14': ('manual_llm_follow_up', 'Manual LLM Follow Up - Analyze previous LLM decision.'),
    '15': ('call_it_a_day', 'Call It a Day - End the current run and save progress.'),
}

MENU_HEADER = """
=========== Blue Prince ML Control Menu ==========="""

MENU_FOOTER = """
q. Quit                     - Exit the script.
"""

# Terminal commands mapping
TERMINAL_COMMANDS = {
    "RUN EXPERIMENT SETUP": "handle_lab_experiment",
    "VIEW ESTATE INVENTORY": "handle_estate_inventory", 
    "ALTER SECURITY LEVEL": "handle_security_level",
    "ALTER MODE": "handle_mode",
    "RUN PAYROLL": "handle_payroll",
    "SPREAD GOLD IN ESTATE": "handle_gold_spread",
    "TIME LOCK SAFE": "handle_time_lock_safe",
}

# Switch actions mapping
SWITCH_ACTIONS = [
    "toggle_keycard_entry_switch", 
    "toggle_gymnasium_switch", 
    "toggle_darkroom_switch", 
    "toggle_garage_switch"
] 