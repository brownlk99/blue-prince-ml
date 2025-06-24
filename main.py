import time
import easyocr
import argparse
import os
from game_state import GameState
from llm_agent import BluePrinceAgent
from capture.resources import capture_resources
from capture.note_capture import capture_note
from capture.vision_utils import get_current_room
from capture.drafting import capture_drafting_options
from capture.items import capture_items
from capture.shops import stock_shelves
from capture.constants import DIRECTORY
from capture.lab import capture_lab_experiment_options

from google.cloud import vision

from room import CoatCheck, PuzzleRoom, SecretPassage, ShopRoom, UtilityCloset
from terminal import SecurityTerminal, ShelterTerminal, Terminal

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
14. Manual LLM Follow Up    - Analyze previous LLM decision.

q. Quit                     - Exit the script.
""")

def main(day, load, verbose, editor_path):
    game_state = None
    if load:
        game_state = GameState.load_from_file(load)
    else:
        game_state = GameState(current_day=day)
    google_client = vision.ImageAnnotatorClient()
    reader = easyocr.Reader(['en'], gpu=True)
    agent = BluePrinceAgent(game_state, verbose)

    #clearing memory if a completely fresh run
    if agent.game_state.day == 1 and not load:
        agent.room_memory.reset()
        agent.term_memory.reset()
        agent.decision_memory.reset()
    elif load:
         # Search through decisions in reverse order (most recent first)
        for decision in reversed(agent.decision_memory.decisions):
            # Check if this decision contains exploration data
            if isinstance(decision, dict) and "target_room" in decision and "final_door" in decision:
                agent.previously_chosen_room = decision["target_room"]
                agent.previously_chosen_door = decision["final_door"]
                break
        
        # If no exploration decision found, keep current values or set defaults
        if not agent.previously_chosen_room:
            print("No previous exploration decision found in memory.")

    print("Script is running. Type a number (1-14) and press Enter to interact. Type 'q' to quit.")

    while True:
        print_menu()
        user_input = input("\nEnter command (1-14, q to quit): ").strip().lower()
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
            if not agent.game_state.current_room:
                print("Could not determine the current room")
                continue
            note = capture_note(google_client, agent.game_state.current_room, editor_path)
            response = agent.generate_note_title(note.content)
            parsed_response = agent.parse_note_title_response(response)
            note.title = parsed_response
            agent.note_memory.add_to_vector_db(note)
            agent.note_memory.add_to_json(note)
            print("Note captured and saved.")
        elif user_input == '3':
            print("Capturing items...")
            item_val = capture_items(google_client)
            if item_val == "Screenshot capture was cancelled.":
                print(item_val)
            elif isinstance(item_val, dict):
                current_item, item_description = next(iter(item_val.items()))
                agent.game_state.items.update({current_item:item_description})                 #update the current items in the game state
                agent.term_memory.automated_add_term(current_item, item_description)
                print("Items captured and saved.")           #add the item to persistent memory in order to make better informed decisions
            elif item_val is None:
                print("No item was captured.")
            else:
                print(f"Unexpected return value: {item_val}")
        elif user_input == '4':
            print("Stocking shelves...")
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            if isinstance(agent.game_state.current_room, ShopRoom):
                stock_shelves(reader, agent.game_state.current_room)        #add items to the current room's shop
                print("Shelves stocked.")
            else:
                print("Current room is not a SHOP ROOM, cannot stock shelves.")
        elif user_input == '5':
            #always update the current room and position before making a decision
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            if agent.game_state.current_room is not None:
                agent.game_state.current_position = agent.game_state.current_room.position
            else:
                print("Current room position is not set.")
                continue

            #always capture the current resources before making a decision
            current_resources = capture_resources(google_client, agent.game_state.resources)
            agent.game_state.resources.update(current_resources)
            agent.game_state.edit_resources()
            
            context = agent.game_state.summarize_for_llm()
            response = agent.take_action(context)
            parsed_response = agent.parse_action_response(response)
            parsed_response["context"] = context
            agent.decision_memory.add_decision(parsed_response)
            print(f"Action Response:\nAction: {parsed_response['action']}\nExplanation: {parsed_response['explanation']}")
            time.sleep(2)
            if parsed_response["action"] == "explore":
                response = agent.decide_door_to_explore(context)
                parsed_response = agent.parse_door_exploration_response(response)
                parsed_response["context"] = context
                agent.decision_memory.add_decision(parsed_response)
                print(f"Explore Response:\nRoom: {parsed_response['room']}\nDoor: {parsed_response['door']}\nPath: {parsed_response['path']}\nSpecial Item: {parsed_response['special_item']}\nExplanation: {parsed_response['explanation']}")
                if parsed_response["special_item"] != "NONE":
                    if parsed_response["special_item"] in agent.game_state.items.keys():
                        agent.game_state.items.pop(parsed_response["special_item"])
                    else:
                        print(f"Special item {parsed_response['special_item']} not found in inventory.")
                time.sleep(2)
            elif parsed_response["action"] == "peruse_shop":
                if isinstance(agent.game_state.current_room, ShopRoom):
                    stock_shelves(reader, agent.game_state.current_room)
                else:
                    print("Current room is not a shop room, cannot stock shelves.")
                print("Stocked shelves")
            elif parsed_response["action"] == "purchase_item":
                response = agent.decide_purchase_item(context)
                parsed_response = agent.parse_purchase_response(response)
                parsed_response["context"] = context
                agent.decision_memory.add_decision(parsed_response)
                print(f"Purchase Response:\nItem: {parsed_response['item']}\nQuantity: {parsed_response['quantity']}\nExplanation: {parsed_response['explanation']}")
                agent.game_state.purchase_item()       #up to the user to alter the quantity of inventory if an item sells out
            elif parsed_response["action"] == "solve_puzzle":
                response = agent.solve_parlor_puzzle(reader, context, editor_path)
                parsed_response = agent.parse_parlor_response(response)
                parsed_response["context"] = context
                agent.decision_memory.add_decision(parsed_response)
                print(f"Parlor Response:\nBox: {parsed_response['box']}\nExplanation: {parsed_response['explanation']}")
                if isinstance(agent.game_state.current_room, PuzzleRoom):
                    agent.game_state.current_room.has_been_solved = True
                else:
                    print("Current room is not a PUZZLE ROOM, cannot mark as solved.")
            elif parsed_response["action"] == "open_secret_passage":
                response = agent.open_secret_passage(context)
                parsed_response = agent.parse_secret_passage_response(response)
                parsed_response["context"] = context
                agent.decision_memory.add_decision(parsed_response)
                print(f"Secret Passage Response:\nRoom Type: {parsed_response['room_type']}\nExplanation: {parsed_response['explanation']}")
                if isinstance(agent.game_state.current_room, SecretPassage):
                    agent.game_state.current_room.has_been_used = True
                else:
                    print("Current room is not a SECRET PASSAGE, cannot mark as used.")
            elif parsed_response["action"] == "dig":
                agent.game_state.current_room.set_dig_spots()
            elif parsed_response["action"] == "open_trunk":
                agent.game_state.current_room.set_trunks()
            elif parsed_response["action"] == "use_terminal":
                if agent.game_state.current_room.terminal:
                    response = agent.use_terminal(context)
                    parsed_response = agent.parse_terminal_response(response)
                    parsed_response["context"] = context
                    agent.decision_memory.add_decision(parsed_response)
                    print(f"Terminal Response:\nCommand: {parsed_response['command']}\nExplanation: {parsed_response['explanation']}")
                    command = parsed_response.get("command", "").upper()
                    if command == "RUN EXPERIMENT SETUP":
                        options = capture_lab_experiment_options(google_client, editor_path)
                        response = agent.decide_lab_experiment(options, context)
                        parsed_response = agent.parse_lab_experiment_response(response)
                        parsed_response["context"] = context
                        agent.decision_memory.add_decision(parsed_response)
                        print(f"Lab Experiment Response:\nCause: {parsed_response.get('cause', 'N/A')}\nEffect: {parsed_response.get('effect', 'N/A')}\nExplanation: {parsed_response.get('explanation', 'N/A')}")
                    elif command == "VIEW ESTATE INVENTORY":
                        if isinstance(agent.game_state.current_room.terminal, SecurityTerminal):
                            agent.game_state.current_room.terminal.set_estate_inventory()
                        else:
                            print("Current room does not have a SECURITY TERMINAL, cannot view estate inventory.")  #TODO: maybe this should be validated by room idk.. i.e. SECURITY ROOM
                        #TODO: implement this.. not sure where to save it......
                    elif command == "ALTER SECURITY LEVEL":
                        response = agent.decide_security_level(context)
                        parsed_response = agent.parse_security_level_response(response)
                        parsed_response["context"] = context
                        agent.decision_memory.add_decision(parsed_response)
                        print(f"Security Level Response:\nLevel: {parsed_response['security_level']}\nExplanation: {parsed_response['explanation']}")
                        if isinstance(agent.game_state.current_room.terminal, SecurityTerminal):
                            agent.game_state.current_room.terminal.set_security_level(parsed_response.get("level", "MEDIUM"))
                        else:
                            print("Current room does not have a SECURITY TERMINAL, cannot alter security level.")
                    elif command == "ALTER MODE":
                        response = agent.decide_mode(context)
                        parsed_response = agent.parse_mode_response(response)
                        parsed_response["context"] = context
                        agent.decision_memory.add_decision(parsed_response)
                        print(f"Mode Response:\nMode: {parsed_response['mode']}\nExplanation: {parsed_response['explanation']}")
                        if isinstance(agent.game_state.current_room.terminal, SecurityTerminal):
                            agent.game_state.current_room.terminal.set_mode(parsed_response.get("mode", "LOCKED"))
                        else:
                            print("Current room does not have a SECURITY TERMINAL, cannot alter mode.")
                    elif command == "TIME LOCK SAFE":       #TODO: SHELTER terminal still needs to be implemented
                        if isinstance(agent.game_state.current_room.terminal, ShelterTerminal):
                            # response = agent.shelter_decide_time_lock_safe()
                            pass
                        else:
                            print("Current room does not have a SHELTER TERMINAL, cannot time lock safe.")
                else:
                    print("No terminal found in the current room.")
                    time.sleep(1)
            elif parsed_response["action"] == "store_item_in_coat_check":
                response = agent.coat_check_prompt("STORE", context)
                parsed_response = agent.parse_coat_check_response(response)
                parsed_response["context"] = context
                agent.decision_memory.add_decision(parsed_response)
                coat_check = agent.game_state.house.get_room_by_name("COAT CHECK")
                print(f"Coat Check Response:\nItem: {parsed_response['item']}\nExplanation: {parsed_response['explanation']}")
                if parsed_response["item"] in agent.game_state.items and isinstance(coat_check, CoatCheck):
                    coat_check.stored_item = parsed_response["item"]
                    print(f"Stored {parsed_response['item']} in Coat Check.")
                elif not coat_check:
                    print("No COAT CHECK room found in the house, cannot store item.")
                else:
                    print(f"Item {parsed_response['item']} not found in inventory.")
            elif parsed_response["action"] == "retrieve_item_from_coat_check":     # TODO: maybe I should use current room instead of if it's just in the house
                response = agent.coat_check_prompt("RETRIEVE", context)
                parsed_response = agent.parse_coat_check_response(response)
                parsed_response["context"] = context
                agent.decision_memory.add_decision(parsed_response)
                coat_check = agent.game_state.house.get_room_by_name("COAT CHECK")
                if isinstance(coat_check, CoatCheck) and coat_check.stored_item == parsed_response["item"]: # if the Coat Check room exists in the house and the stored item matches the requested item
                    agent.game_state.items[parsed_response["item"]] = DIRECTORY["ITEMS"][parsed_response["item"]]
                    coat_check.stored_item = ""
                    print(f"Retrieved {parsed_response['item']} from Coat Check.")
                elif not coat_check:
                    print("No COAT CHECK room found in the house, cannot retrieve item.")
                else:
                    print(f"Item {parsed_response['item']} not found in Coat Check.")
                print(f"Coat Check Response:\nItem: {parsed_response['item']}\nExplanation: {parsed_response['explanation']}")
            elif parsed_response["action"] in ["toggle_keycard_entry_switch", "toggle_gymnasium_switch", "toggle_darkroom_switch", "toggle_garage_switch"]:
                utility_closet = agent.game_state.house.get_room_by_name("UTILITY CLOSET")
                if isinstance(utility_closet, UtilityCloset):
                   switch_name = parsed_response["action"].replace("toggle_", "")
                   utility_closet.toggle_switch(switch_name)
                else:
                    print("No UTILITY CLOSET found in the house, cannot toggle switches.")
            elif parsed_response["action"] == "call_it_a_day":
                agent.game_state.save_to_file(f'./jsons/runs/day_{agent.game_state.day}.json')    #call it a day
                reason_for_ending = input("Reason for ending the run: ")
                coat_check = agent.game_state.house.get_room_by_name("COAT CHECK")
                previous_run = agent.previous_run_memory.get_most_recent_run()
                previous_stored_item = previous_run.get("stored_item", "")
                stored_item = ""
                if isinstance(coat_check, CoatCheck):
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
            if agent.game_state.current_room is not None:
                agent.game_state.current_position = agent.game_state.current_room.position
            else:
                print("Current ROOM position is not set.")
                continue

            #always capture the current resources before making a decision
            current_resources = capture_resources(google_client, agent.game_state.resources)
            agent.game_state.resources.update(current_resources)
            agent.game_state.edit_resources()

            #get the previously chosen room and door from the agent
            room = agent.game_state.house.get_room_by_name(agent.previously_chosen_room)
            if room is not None:
                chosen_door = room.get_door_by_orientation(agent.previously_chosen_door)
            else:
                print("Previously chosen room not found, cannot DRAFT.")
                continue

            drafting_options = capture_drafting_options(reader, google_client, room, chosen_door)
            context = agent.game_state.summarize_for_llm()
            response = agent.decide_drafting_option(drafting_options, context)
            parsed_response = agent.parse_drafting_response(response)
            parsed_response["context"] = context
            agent.decision_memory.add_decision(parsed_response)
            if "action" in parsed_response:
                print(f"Drafting Response:\nAction: {parsed_response['action']}\nType: {parsed_response['type']}\nExplanation: {parsed_response['explanation']}")
                print("\nLLM requested a REDRAW. Returning to menu. Select option 6 again after REDRAW.")
                time.sleep(1)
                # TODO: decrement redraw counter? (manual for now)
                continue  # return to menu
            elif "room" in parsed_response:
                print(f"Drafting Response:\nRoom: {parsed_response['room']}\nEnter: {parsed_response['enter']}\nExplanation: {parsed_response['explanation']}")
                
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
                        continue
                
                # Check if player can afford the room
                if selected_room.cost > agent.game_state.resources.get("gems", 0):
                    print(f"\nNot enough resources to draft {selected_room.name}. Cost: {selected_room.cost}, Available: {agent.game_state.resources.get('GEMS', 0)}")
                    print("Returning to menu. Please select option 6 again to draft a room.")
                    time.sleep(1)
                    continue

                if selected_room.name == "UNKNOWN" or selected_room.name == "ARCHIVED FLOOR PLAN":
                    room_name = input("Please enter the name of the newly drafted room: ").strip().upper()
                    agent.game_state.house.autofill_room_attributes(selected_room, room_name)
                    selected_room = agent.game_state.house.specialize_room(selected_room)      

                # Add room to house and handle additional operations
                agent.game_state.house.add_room_to_house(selected_room)
                
                agent.game_state.house.connect_adjacent_doors(selected_room)
                agent.room_memory.add_room(selected_room) # add to room memory and save game state

                # Handle room entry if requested
                if parsed_response.get("enter", "").upper() == "YES":
                    selected_room.has_been_entered = True
                    if len(selected_room.doors) > 1:  # If multiple doors, prompt for editing
                        print("\nPlease enter the room and edit the doors within the newly drafted room to ensure accuracy.")
                        selected_room.edit_doors()

                agent.game_state.save_to_file('./jsons/current_run.json')
                print(agent.game_state.house.print_map())
        elif user_input == '7':
            agent.term_memory.user_facilitated_add_term()
        elif user_input == '8':
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            if agent.game_state.current_room is not None:
                agent.game_state.current_room.set_dig_spots()
            else:
                print("Current ROOM is not set, cannot set dig spots.")
                continue
        elif user_input == '9':
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            if agent.game_state.current_room is not None:
                agent.game_state.current_room.set_trunks()
            else:
                print("Current ROOM is not set, cannot set trunks.")
                continue
        elif user_input == '10':
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            if agent.game_state.current_room is not None:
                agent.game_state.current_room.edit_doors()
                agent.game_state.house.connect_adjacent_doors(agent.game_state.current_room)  # ensure doors are connected after editing
            else:
                print("Current ROOM is not set, cannot edit doors.")
                continue
        elif user_input == '11':
            agent.game_state.current_room = get_current_room(reader, agent.game_state.house)
            if isinstance(agent.game_state.current_room, ShopRoom):
                agent.game_state.current_room.edit_items_for_sale()
            else:
                print("Current ROOM is not a SHOP ROOM, cannot edit items for sale.")
                continue
        elif user_input == '12':    # can update without being within the room
            # get all rooms with name "UNKNOWN" that need attributes filled
            potential_rooms_to_edit = agent.game_state.house.get_rooms_by_name("UNKNOWN")
            
            # early exit if no UNKNOWN rooms exist
            if not potential_rooms_to_edit:
                print("No rooms to autofill attributes for.")
                time.sleep(1)
                continue
            
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
                    continue
            
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
        elif user_input == '14':
            response = agent.manual_llm_follow_up()
            print(f"Manual LLM Follow Up Response:\n{response}")
        else:
            print("Invalid input. Please enter a number between 1 and 14, or 'q' to quit.")
            time.sleep(1)
        agent.game_state.save_to_file('./jsons/current_run.json')   #always save to file after

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--load', '-l', type=str, help='Path to saved game state JSON')
    parser.add_argument('--day', '-d', type=int, required=True, help='Day/run number for this session')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show full LLM prompts')
    parser.add_argument('--editor', '-e', type=str, default=os.environ.get('EDITOR_PATH'), help='Path to text editor (default: from EDITOR_PATH env var)')
    args = parser.parse_args()

    main(args.day, args.load, args.verbose, args.editor)