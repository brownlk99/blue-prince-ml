import time
import easyocr
import json
import argparse
from game_state import GameState
from llm_agent import BluePrinceAgent
from utils import append_to_list_json, update_json
from capture.resources import capture_resources
from capture.note_capture import capture_note
from capture.vision_utils import get_current_room, get_current_room_name
from capture.drafting import capture_drafting_options
from capture.items import capture_items
from capture.shops import stock_shelves
from capture.constants import ROOM_LOOKUP, DIRECTORY, ROOM_LIST
from capture.lab import capture_lab_experiment_options

from google.cloud import vision

from door import Door
from house_map import HouseMap
from room import Room
from terminal import Terminal, SecurityTerminal, LabTerminal, OfficeTerminal, ShelterTerminal

def print_menu():
    print("""
=== Blue Prince ML Control Menu ===
1. Capture Resources        - Use OCR to capture and update resource counts.
2. Capture Note             - Capture a note for the current room.
3. Capture Items            - Use OCR to capture and update items.
4. Stock Shelves            - Stock shelves in the current room.
5. Take Action              - Use LLM to decide on actions based on current state.
6. Drafting Options         - Capture drafting options for the current room.
7. Add Term to Memory       - Add a term to memory.
8. Set Dig Spots            - Set dig spots in the current room.
9. Set Trunks               - Set trunks in the current room.
10. Edit Doors              - Edit doors in the current room.
11. Edit Items for Sale     - Edit items for sale in the current room.
12. Fill Room Attributes    - Autofill attributes for a room based on its position.
13. Save Game State         - Save the current game state to a JSON file.

q. Quit                     - Exit the script.
""")

def main(game_state):
    google_client = vision.ImageAnnotatorClient()
    reader = easyocr.Reader(['en'], gpu=True)
    agent = BluePrinceAgent(game_state)

    #if loading a game state, set the LLM's last decision
    if agent.game_state.house.count_occupied_rooms() > 2:
        while True:
            prev_room = input("Previously chosen room: ").upper()
            if prev_room in ROOM_LIST:
                agent.previously_chosen_room = prev_room
                break
            print(f"Invalid room. Please choose from: {ROOM_LIST}")

        while True:
            prev_door = input("Previously chosen door: ").upper()
            if prev_door in ["N", "S", "E", "W"]:
                agent.previously_chosen_door = prev_door
                break
            print("Invalid door. Please choose from: N, S, E, W")

    #clearing memory if a new run
    if agent.game_state.day == 1:
        agent.room_memory.reset()
        agent.term_memory.reset()

    print("Script is running. Type a number (1-13) and press Enter to interact. Type 'q' to quit.")

    while True:
        print_menu()
        user_input = input("\nEnter command (1-13, q to quit): ").strip().lower()
        if user_input == 'q':
            print("Exiting script.")
            break

        if user_input == '1':
            print("Capturing resources...")
            current_resources = capture_resources(google_client)
            agent.game_state.resources.update(current_resources)
            print("Resources captured and saved.")
        elif user_input == '2':
            print("Capturing note...")
            note = capture_note(google_client, agent.game_state.current_room)
            response = agent.generate_note_title(note.content)
            parsed_response = agent.parse_note_title_response(response)
            note.title = parsed_response
            agent.note_memory.add_to_vector_db(note)
            agent.note_memory.add_to_json(note)
            print("Note captured and saved.")
        elif user_input == '3':
            print("Capturing items...")
            current_item = capture_items(google_client)
            agent.game_state.items.update(current_item)                 #update the current items in the game state
            agent.memory.automated_add_term(current_item)               #add the item to persistent memory in order to make better informed decisions
            print("Items captured and saved.")
        elif user_input == '4':
            print("Stocking shelves...")
            stock_shelves(reader, agent.game_state.current_room)        #add items to the current room's shop
            print("Shelves stocked.")
        elif user_input == '5':
            #always update the current room and position before making a decision
            current_room = get_current_room(reader, agent.game_state.house)
            agent.game_state.current_room = current_room
            agent.game_state.current_position = current_room.position

            #always capture the current resources before making a decision
            current_resources = capture_resources(google_client)
            agent.game_state.resources.update(current_resources)
            agent.game_state.edit_resources()
            
            response = agent.take_action()
            print("\nLLM Response:\n", response)
            action, explanation = agent.parse_action_response(response)
            print(f"Parsed Action: {action}\nExplanation: {explanation}")
            if action == "explore":
                response = agent.decide_door_to_explore()
                print("\n LLM Response:\n", response)
                parsed_response = agent.parse_door_exploration_response(response)
            elif action == "peruse_shop":
                stock_shelves(reader, agent.game_state.current_room)
            elif action == "purchase_item":
                response = agent.decide_purchase_item()
                print("\nLLM Response:\n", response)
                agent.game_state.purchase_item()       #up to the user to alter the quantity of inventory if an item sells out
            elif action == "solve_puzzle":
                response = agent.solve_parlor_puzzle(reader)
                agent.game_state.current_room.has_been_solved = True
                print("\nLLM Response:\n", response)
            elif action == "dig":
                agent.game_state.current_room.set_dig_spots()
            elif action == "open_trunk":
                agent.game_state.current_room.set_trunks()
            elif action == "use_terminal":
                if agent.game_state.current_room.terminal:
                    response = agent.use_terminal()
                    parsed_response = agent.parse_terminal_response(response)
                    print("\nLLM Response:\n", parsed_response)
                    command = parsed_response.get("command", "").upper()
                    if command == "RUN EXPERIMENT SETUP":
                        options = capture_lab_experiment_options(google_client)
                        response = agent.decide_lab_experiment(options)
                        parsed_response = agent.parse_lab_experiment_response(response)
                        print("\nLLM Response:\n", parsed_response)
                    elif command == "VIEW ESTATE INVENTORY":
                        agent.game_state.current_room.terminal.set_estate_inventory()
                        #TODO: implement this.. not sure where to save it......
                    elif command == "ALTER SECURITY LEVEL":
                        response = agent.decide_security_level()
                        parsed_response = agent.parse_security_level_response(response)
                        print("\nLLM Response:\n", parsed_response)
                        agent.game_state.current_room.terminal.set_security_level(parsed_response.get("level", "MEDIUM"))
                    elif command == "ALTER MODE":
                        response = agent.decide_mode()
                        parsed_response = agent.parse_mode_response(response)
                        print("\nLLM Response:\n", parsed_response)
                        agent.game_state.current_room.terminal.set_mode(parsed_response.get("mode", "LOCKED"))
                    elif command == "TIME LOCK SAFE":       #TODO: SHELTER terminal still needs to be implemented
                        response = agent.shelter_decide_time_lock_safe()
                else:
                    print("No terminal found in the current room.")
                    time.sleep(1)
            elif action == "store_item_in_coat_check":
                response = agent.coat_check_prompt("STORE")
                parsed_response = agent.parse_coat_check_response(response)
                coat_check = agent.game_state.house.get_room_by_name("COAT CHECK")
                print("\nLLM Response:\n", parsed_response)
                if parsed_response["item"] in agent.game_state.items and coat_check: # if item exists in the player's inventory and the Coat Check room exists in the house
                    coat_check.stored_item = parsed_response["item"]
                    print(f"Stored {parsed_response['item']} in Coat Check.")
                elif not coat_check:
                    print("No Coat Check room found in the house.")
                else:
                    print(f"Item {parsed_response['item']} not found in inventory.")
            elif action == "retrieve_item_from_coat_check":     # TODO: maybe I should use current room instead of if it's just in the house
                response = agent.coat_check_prompt("RETRIEVE")
                parsed_response = agent.parse_coat_check_response(response)
                coat_check = agent.game_state.house.get_room_by_name("COAT CHECK")
                if coat_check and coat_check.stored_item == parsed_response["item"]: # if the Coat Check room exists in the house and the stored item matches the requested item
                    agent.game_state.items[parsed_response["item"]] = DIRECTORY["ITEMS"][parsed_response["item"]]
                    coat_check.stored_item = ""
                    print(f"Retrieved {parsed_response['item']} from Coat Check.")
                elif not coat_check:
                    print("No Coat Check room found in the house.")
                else:
                    print(f"Item {parsed_response['item']} not found in Coat Check.")
                print("\nLLM Response:\n", parsed_response)
            elif action in ["toggle_keycard_entry_switch", "toggle_gymnasium_switch", "toggle_darkroom_switch", "toggle_garage_switch"]:
                utility_closet = agent.game_state.house.get_room_by_name("UTILITY CLOSET")
                if utility_closet:
                   switch_name = action.replace("toggle_", "")
                   utility_closet.toggle_switch(switch_name)
                else:
                    print("No Utility Closet found in the house.")
            elif action == "call_it_a_day":
                agent.game_state.save_to_file(f'./jsons/runs/day_{agent.game_state.day}.json')    #call it a day
                reason_for_ending = input("Reason for ending the run: ")
                coat_check = agent.game_state.house.get_room_by_name("COAT CHECK")
                previous_run = agent.previous_run_memory.get_most_recent_run()
                previous_stored_item = previous_run.get("stored_item", "")
                stored_item = ""
                if coat_check:
                    # player interacted with coat check this run
                    current_stored_item = coat_check.stored_item

                    if current_stored_item != previous_stored_item:
                        # player swapped out or added a new item
                        stored_item = current_stored_item
                    else:
                        # player did not exchange any item, keep previous
                        stored_item = previous_stored_item
                else:
                    # coat check not present, keep previous stored item
                    stored_item = previous_stored_item
                agent.previous_run_memory.add_run(agent.game_state.day, reason_for_ending, stored_item)

        elif user_input == '6':
            #always update the current room and position before making a decision
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            agent.game_state.current_position = agent.game_state.current_room.position

            #get the previously chosen room and door from the agent
            room = agent.game_state.house.get_room_by_name(agent.previously_chosen_room)
            chosen_door = room.get_door_by_orientation(agent.previously_chosen_door)

            drafting_options = capture_drafting_options(reader, google_client, room, chosen_door)
            response = agent.decide_drafting_option(drafting_options)
            parsed_response = agent.parse_drafting_response(response)
            print("\nLLM Response:\n", parsed_response)
            if parsed_response.get("action", "").upper() == "REDRAW":   # if the LLM requested a redraw
                print("\nLLM requested a REDRAW. Returning to menu. Select option 6 again after REDRAW.")
                time.sleep(1)
                # TODO: decrement redraw counter (manual for now)
                break  # return to menu

            for drafted_room in drafting_options:                       # if no redraw, iterate through the drafted rooms and add the one that matches the LLM's response
                if drafted_room.name == parsed_response["room"].upper():
                    if parsed_response.get("enter", "").upper() == "YES":
                        drafted_room.has_been_entered = True
                        drafted_room.edit_doors()
                    agent.game_state.house.add_room_to_house(drafted_room)
                    agent.game_state.house.connect_adjacent_doors(drafted_room)
                    agent.room_memory.add_room(drafted_room)
                    break       # stop loop, save, and return to menu
            agent.game_state.save_to_file('./jsons/current_run.json')

            print(agent.game_state.house.print_map())
        elif user_input == '7':
            agent.term_memory.user_facilitated_add_term()
        elif user_input == '8':
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            agent.game_state.current_room.set_dig_spots()
        elif user_input == '9':
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            agent.game_state.current_room.set_trunks()
        elif user_input == '10':
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            agent.game_state.current_room.edit_doors()
        elif user_input == '11':
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            agent.game_state.current_room.edit_items_for_sale()
        elif user_input == '12':
            potential_rooms_to_edit = agent.game_state.house.get_rooms_by_name("UNKNOWN")
            if not potential_rooms_to_edit:
                print("No rooms to autofill attributes for.")
                time.sleep(1)
                break
            else:
                print("Select a room to edit:")
                for idx, room in enumerate(potential_rooms_to_edit):
                    print(f"{idx + 1}: Position: {room.position}")
                selection = input("Enter the number of the room to edit based off of position (upper left corner is 0,0): ").strip()
                if selection.isdigit() and 1 <= int(selection) <= len(potential_rooms_to_edit):
                    room_to_edit = potential_rooms_to_edit[int(selection) - 1]
                    room_name = input("Please enter the name of the room to edit attributes for: ").strip().upper()
                    agent.game_state.house.autofill_room_attributes(room_to_edit, room_name)
                    agent.game_state.house.specialize_room(room_to_edit)
                else:
                    print("Invalid selection.")
        elif user_input == '13':
            agent.game_state.save_to_file('./jsons/current_run.json')
        else:
            print("Invalid input. Please enter a number between 1 and 10, or 'q' to quit.")
            time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--load', type=str, help='Path to saved game state JSON')
    parser.add_argument('--day', type=int, required=True, help='Day/run number for this session')
    args = parser.parse_args()

    if args.load:
        game_state = GameState.load_from_file(args.load)
    else:
        game_state = GameState(current_day=args.day)
    main(game_state)