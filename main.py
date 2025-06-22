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
from capture.items import capture_items, manually_obtain_item
from capture.shops import stock_shelves
from capture.constants import ROOM_LOOKUP, DIRECTORY, ROOM_LIST
from capture.lab import capture_lab_experiment_options

from google.cloud import vision

from door import Door
from house_map import HouseMap
from room import Room, ShopRoom, PuzzleRoom, CoatCheck, UtilityCloset
from terminal import Terminal, SecurityTerminal, LabTerminal, OfficeTerminal, ShelterTerminal

def print_menu():
    print("""
=========== Blue Prince ML Control Menu ===========
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
    if agent.game_state.house.count_occupied_rooms() > 2:   # TODO: clarify this a little more
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
            current_resources = capture_resources(google_client, agent.game_state.resources)
            agent.game_state.resources.update(current_resources)
            print("Resources captured and saved.")
        elif user_input == '2':
            print("Capturing note...")
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            note = capture_note(google_client, agent.game_state.current_room)
            response = agent.generate_note_title(note.content)
            parsed_response = agent.parse_note_title_response(response)
            note.title = parsed_response
            agent.note_memory.add_to_vector_db(note)
            agent.note_memory.add_to_json(note)
            print("Note captured and saved.")
        elif user_input == '3':
            print("Capturing items...")
            item_val = capture_items(google_client)     #TODO: this is so gross
            if item_val == "Screenshot capture was cancelled.":
                print(item_val)
            elif item_val is not None:
                current_item, item_description = next(iter(item_val.items()))
                agent.game_state.items.update({current_item:item_description})                 #update the current items in the game state
                agent.term_memory.automated_add_term(current_item, item_description)
                print("Items captured and saved.")           #add the item to persistent memory in order to make better informed decisions
            else:
                print("OCR did not recognize the item. Please enter manually.")
                manual_item, manual_description = manually_obtain_item()
                if manual_item is not None:
                    agent.game_state.items.update({manual_item: manual_description})
                    agent.term_memory.automated_add_term(manual_item, manual_description)
                    print("Item manually entered and saved.")
                else:
                    print("No item was entered.")
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
            current_resources = capture_resources(google_client, agent.game_state.resources)
            agent.game_state.resources.update(current_resources)
            agent.game_state.edit_resources()
            
            response = agent.take_action()
            action, explanation = agent.parse_action_response(response)
            print(f"Parsed Response:\nAction: {action}\nExplanation: {explanation}")
            time.sleep(2)
            if action == "explore":
                response = agent.decide_door_to_explore()
                parsed_response = agent.parse_door_exploration_response(response)
                print(f"Parsed Explore Response:\nRoom: {parsed_response['room']}\nDoor: {parsed_response['door']}\nPath: {parsed_response['path']}\nExplanation: {parsed_response['explanation']}")
                time.sleep(2)
            elif action == "peruse_shop":
                stock_shelves(reader, agent.game_state.current_room)
                print("Stocked shelves")
            elif action == "purchase_item":
                response = agent.decide_purchase_item()
                parsed_response = agent.parse_purchase_response(response)
                print(f"Parsed Purchase Response:\nItem: {parsed_response['item']}\nQuantity: {parsed_response['quantity']}\nExplanation: {parsed_response['explanation']}")
                agent.game_state.purchase_item()       #up to the user to alter the quantity of inventory if an item sells out
            elif action == "solve_puzzle":
                response = agent.solve_parlor_puzzle(reader)
                parsed_response = agent.parse_parlor_response(response)
                print(f"Parsed Parlor Response:\nBox: {parsed_response['box']}\nExplanation: {parsed_response['explanation']}")
                agent.game_state.current_room.has_been_solved = True
            elif action == "open_secret_passage":
                response = agent.open_secret_passage()
                parsed_response = agent.parse_secret_passage_response(response)
                print(f"Parsed Secret Passage Response:\nRoom Type: {parsed_response['room_type']}\nExplanation: {parsed_response['explanation']}")
                current_room.has_been_used = True
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
            if "action" in parsed_response:
                print(f"LLM Response:\nAction: {parsed_response['action']}\nType: {parsed_response['type']}\nExplanation: {parsed_response['explanation']}")
                print("\nLLM requested a REDRAW. Returning to menu. Select option 6 again after REDRAW.")
                time.sleep(1)
                # TODO: decrement redraw counter? (manual for now)
                break  # return to menu
            elif "room" in parsed_response:
                print(f"LLM Response:\nRoom: {parsed_response['room']}\nEnter: {parsed_response['enter']}\nExplanation: {parsed_response['explanation']}")
                
                # Check if we're dealing with unknown rooms
                all_unknown = all(option.name == "UNKNOWN" for option in drafting_options)
                selected_room = None
                
                if all_unknown:
                    # Handle case where all rooms are UNKNOWN (dark room effect)
                    print("All drafts are UNKNOWN due to dark room effect. Using generic UNKNOWN room.")
                    selected_room = drafting_options[0]
                else:
                    # Find the room that matches the LLM's selection
                    room_name = parsed_response["room"].upper()
                    selected_room = next((room for room in drafting_options if room.name == room_name), None)
                    
                    if not selected_room:
                        print(f"Error: Selected room '{room_name}' not found in drafting options.")
                        time.sleep(1)
                        break
                
                # Check if player can afford the room
                if selected_room.cost > agent.game_state.resources.get("GEMS", 0):
                    print(f"\nNot enough resources to draft {selected_room.name}. Cost: {selected_room.cost}, Available: {agent.game_state.resources.get('GEMS', 0)}")
                    print("Returning to menu. Please select option 6 again to draft a room.")
                    time.sleep(1)
                    break

                if selected_room.name == "UNKNOWN" or selected_room.name == "ARCHIVED FLOOR PLAN":
                    room_name = input("Please enter the name of the newly drafted room: ").strip().upper()
                    agent.game_state.house.autofill_room_attributes(selected_room, room_name)
                    selected_room = agent.game_state.house.specialize_room(selected_room)      

                # Add room to house and handle additional operations
                agent.game_state.house.add_room_to_house(selected_room)
                
                # Handle room entry if requested
                if parsed_response.get("enter", "").upper() == "YES":
                    selected_room.has_been_entered = True
                    if len(selected_room.doors) > 1:  # If multiple doors, prompt for editing
                        print("\nPlease enter the room and edit the doors within the newly drafted room to ensure accuracy.")
                        selected_room.edit_doors()
                
                agent.game_state.house.connect_adjacent_doors(selected_room)
                agent.room_memory.add_room(selected_room) # add to room memory and save game state

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
            agent.game_state.house.connect_adjacent_doors(agent.game_state.current_room)  # ensure doors are connected after editing
        elif user_input == '11':
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            agent.game_state.current_room.edit_items_for_sale()
        elif user_input == '12':    # can update without being within the room
            # get all rooms with name "UNKNOWN" that need attributes filled
            potential_rooms_to_edit = agent.game_state.house.get_rooms_by_name("UNKNOWN")
            
            # early exit if no UNKNOWN rooms exist
            if not potential_rooms_to_edit:
                print("No rooms to autofill attributes for.")
                time.sleep(1)
                break
            
            # select the room to edit
            room_to_edit = None
            if len(potential_rooms_to_edit) == 1:
                # single room case - use it directly
                room_to_edit = potential_rooms_to_edit[0]
            else:
                # multiple rooms case - ask user to select one
                print("Select a room to edit:") 
                for idx, room in enumerate(potential_rooms_to_edit):
                    print(f"{idx + 1}: Position: {room.position}")
                    
                selection = input("Enter the number of the room to edit: ").strip()
                if selection.isdigit() and 1 <= int(selection) <= len(potential_rooms_to_edit):
                    room_to_edit = potential_rooms_to_edit[int(selection) - 1]
                else:
                    print("Invalid selection.")
                    time.sleep(1)
                    break
            
            # proceed with room editing if a valid room was selected
            if room_to_edit:
                # get the new room name
                room_name = input("Please enter the name of the room: ").strip().upper()
                
                # update room attributes and specialized type
                agent.game_state.house.autofill_room_attributes(room_to_edit, room_name)
                room_to_edit = agent.game_state.house.specialize_room(room_to_edit)
                agent.game_state.house.update_room_in_house(room_to_edit)
                print(f"Room updated to {room_name}.")
                
                # update room memory
                agent.room_memory.add_room(room_to_edit)
        elif user_input == '13':
            agent.game_state.save_to_file('./jsons/current_run.json')
        else:
            print("Invalid input. Please enter a number between 1 and 13, or 'q' to quit.")
            time.sleep(1)
        agent.game_state.save_to_file('./jsons/current_run.json')   #always save to file after

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