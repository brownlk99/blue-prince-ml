import json
import time
from typing import Dict, Any, Tuple, Optional, Union

from game.constants import DIRECTORY
from game.door import Door
from game.house_map import HouseMap
from game.room import CoatCheck, PuzzleRoom, Room, SecretPassage, ShopRoom, UtilityCloset
from utils import get_color_code


class GameState:
    """
        Manages the current state of the game including resources, items, rooms, and player position

            Attributes:
                resources (Dict[str, int]): Dictionary of game resources like keys, gems, coins
                items (Dict[str, str]): Dictionary of special items collected
                notes (List[Any]): List of notes found in the game
                house (HouseMap): The current house map containing all rooms
                current_position (Tuple[int, int]): Current x, y coordinates of the player
                current_room (Optional[Room]): The room the player is currently in
                day (int): Current day of the game
                special_order (Optional[str]): Any special order placed at the commissary
    """
    def __init__(self, current_day: int = 1) -> None:
        """
            Initialize a new game state with default values

                Args:
                    current_day: The starting day for the game state
        """
        self.resources = {
            "footprints": 0,
            "dice": 0,
            "keys": 0,
            "gems": 0,
            "coins": 0
        }
        self.items = {}
        self.notes = []
        self.house = HouseMap()
        self.setup_default_rooms()
        self.current_position = (2, 8)
        self.current_room = self.house.get_room_by_position(self.current_position[0], self.current_position[1])
        self.day = current_day
        self.special_order = None

    def setup_default_rooms(self) -> None:
        """
	        Set up the default rooms in the house including entrance hall and antechamber
        """
        entrance_hall = Room(
            name="ENTRANCE HALL",
            shape="T",
            cost=0,
            type=[
                "PERMANENT",
                "BLUEPRINT"
            ],
            doors=[Door(locked="False", orientation="W", is_security="False"), Door(locked="False", orientation="N", is_security="False"), Door(locked="False", orientation="E", is_security="False")],
            description="Past the steps and beyond the grand doors, admission to Mount Holly is granted by way of a dark and garish lobby, suitably called the Entrance Hall. From here, each guest's adventure begins; however, the three doors that proceed onward do not always lead to the same adjoining rooms...",
            additional_info="",
            position=(2, 8),
            rarity="N/A",
            has_been_entered=True
        )
        antechamber = Room(
            name="ANTECHAMBER",
            shape="CROSS",
            cost=0,
            type=[
                "BLUEPRINT",
                "OBJECTIVE"
            ],
            doors=[Door(orientation="W"), Door(orientation="N"), Door(orientation="S"), Door(orientation="E")],
            description="From its root meaning \"The Room Before\", all signs and paths point toward the Antechamber. This mysterious sealed room -resting on the 9th Rank- may prove, however, quite an initial challenge to even each, let alone enter. Still, you can't help but draw a connection between this chamber and Room 46.",
            additional_info="",
            position=(2, 0),
            rarity="N/A"
        )
        self.house.add_room_to_house(entrance_hall)
        self.house.add_room_to_house(antechamber)

    def summarize_for_llm(self) -> str:
        """
            Summarizes the current game state for the LLM

                Returns:
                    A summary of the current state
        """
        x, y = self.current_position
        current_room = self.house.get_room_by_position(x, y)
        summary = [
            f"Resources: {', '.join(f'{k}={v}' for k, v in self.resources.items())}",
            f"Current room position: ({x}, {y})",
            f"Current room: {current_room.name if current_room else 'None'}",       #shouldn't be none for any valid room within the house, but here just in case
            f"House dimensions: width={self.house.width}, height={self.house.height} (upper left corner (most north-west) is (0,0))",
            "Items:"
        ]
        if self.items:
            summary.extend([f"  - {name}: {desc}" for name, desc in self.items.items()])
        else:
            summary.append("  None")
        if self.special_order:
            summary.append(f"Special order for COMMISSARY: {self.special_order}")
        summary.append("Rooms Currently in House:")
        for row in self.house.grid:
            for room in row:
                if room is not None :
                    doors = "      " + " \n      ".join(
                        f"{door.orientation} (leads_to={getattr(door, 'leads_to', None)}, locked={door.locked}, is_security={door.is_security})"
                        for door in (room.doors if isinstance(room.doors, list) else [])
                    )
                    summary.append(f"  - {room.name} at {room.position}, type: {room.type}, rarity: {room.rarity}, has_been_entered: {room.has_been_entered}")
                    # ShopRoom
                    if isinstance(room, ShopRoom):
                        items_for_sale = getattr(room, 'items_for_sale', {})
                        if items_for_sale:
                            summary.append(f"    Items for sale in {room.name}:")
                            for item, price in items_for_sale.items():
                                summary.append(f"      - {item}: {price}")
                        else:
                            summary.append(f"    Items for sale: Unknown ")
                    if isinstance(room, PuzzleRoom):
                        summary.append(f"    Puzzle has been solved: {room.has_been_solved}")
                    # UtilityCloset
                    if isinstance(room, UtilityCloset):
                        summary.append(
                            f"    Utility switches: keycard_entry_system_switch={room.keycard_entry_system_switch}, "
                            f"gymnasium_switch={room.gymnasium_switch}, darkroom_switch={room.darkroom_switch}, "
                            f"garage_switch={room.garage_switch}"
                        )
                    # CoatCheck
                    if isinstance(room, CoatCheck):
                        summary.append(f"    Stored item in Coat Check: {room.stored_item if room.stored_item else 'None'}")
                    # Trunks
                    if getattr(room, "trunks", 0) > 0:
                        summary.append(f"    Trunks in {room.name}: {room.trunks}")
                    # Dig spots
                    if getattr(room, "dig_spots", 0) > 0:
                        summary.append(f"    Dig spots in {room.name}: {room.dig_spots}")
                    # Terminal
                    if getattr(room, "terminal", None) is not None:
                        summary.append(f"    Terminal present in {room.name}: {room.terminal}")
                    summary.append(f"     Doors: \n{doors}")
        summary.append("If a ROOM has_been_entered, it means the player has been in that room at least once to collect the initial items and information regarding its DOORS.")
        return "\n".join(summary)

    def edit_resources(self) -> None:
        """
	        Allow user to interactively edit game resources
        """
        print("\n\n----- EDIT GAME RESOURCES -----")

        while True:
            print("\nCurrent Resources:")
            for key, value in self.resources.items():
                print(f" - {get_color_code(key)}: {value}")

            res_key = input("\nEnter resource name to edit (or press Enter to finish): ").strip().lower()
            if not res_key:
                break

            if res_key not in self.resources:
                print("\nInvalid resource name. Try one of:", ", ".join(self.resources.keys()))
                time.sleep(2)
                continue

            new_val = input(f"New value for {get_color_code(res_key)}: ").strip()
            try:
                self.resources[res_key] = int(new_val)
                print(f"Updated {get_color_code(res_key)} to {new_val}.")
            except ValueError:
                print("\nInvalid number. Please enter an integer.")
                time.sleep(2)
    
    def get_available_redraws(self) -> Dict[str, int]:
        """
            Calculate and return available redraws from different sources

                Returns:
                    Dictionary containing counts of available redraws by type
        """
        dice_redraw_count = self.resources.get("dice", 0)
        room_redraw_count = 0
        study_redraw_count = 0

        if self.current_room and self.current_room.name in ("CLASSROOM", "DRAWING ROOM"):
            while True:
                val = input("\nHow many redraws are allotted by the current room? ")
                if val.isdigit():
                    room_redraw_count = int(val)
                    break
                print("\nInvalid input. Please enter a number.")
                time.sleep(2)
        if self.house.get_room_by_name("STUDY"):
            while True:
                val = input("\nHow many redraws are allotted by the STUDY? ")
                if val.isdigit():
                    study_redraw_count = int(val)
                    break
                print("\nInvalid input. Please enter a number.")
                time.sleep(2)

        return {
            "dice": dice_redraw_count,
            "room": room_redraw_count,
            "study": study_redraw_count
        }

    def purchase_item(self) -> None:
        """
            User-driven function to remove an item from the current room's items_for_sale
        """
        if isinstance(self.current_room, ShopRoom):
            while True:
                items = list(self.current_room.items_for_sale.items())
                if not items:
                    print("No items left for sale in this shop.")
                    break

                print("\nItems for sale:")
                for idx, (item, price) in enumerate(items, 1):
                    print(f"{idx}. {item} - {price} coins")
                print("q. Exit item removal")

                choice = input("Enter the number of the item to remove: ").strip()
                if choice.lower() == 'q':
                    print("Exiting item removal.")
                    break

                try:
                    idx = int(choice) - 1
                    if idx < 0 or idx >= len(items):
                        print("\nPlease enter a valid option.")
                        time.sleep(2)
                        continue
                    item_name = items[idx][0]
                    del self.current_room.items_for_sale[item_name]
                    if item_name == self.special_order:
                        self.special_order = None
                    print(f"Removed {item_name} from items for sale.")
                except Exception as e:
                    print("\nPlease enter a valid option.")
                    time.sleep(2)

    def to_dict(self) -> Dict[str, Any]:
        """
            Convert the game state to a dictionary representation

                Returns:
                    Dictionary containing all game state data
        """
        return {
            "resources": self.resources,
            "current_position": {"x": self.current_position[0], "y": self.current_position[1]},
            "current_room": self.current_room.to_dict() if self.current_room else None,
            "items": self.items,
            "house": self.house.to_dict(),
            "day": self.day,
            "special_order": self.special_order
        }

    def save(self, filepath: str = './jsons/current_run.json') -> None:
        """
            Serialize the game state to a JSON file

                Args:
                    filepath: Path to save the game state JSON file
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def load_from_file(filepath: str) -> 'GameState':
        """
            Load the game state from a JSON file and return a GameState object

                Args:
                    filepath: Path to the JSON file to load
                    
                Returns:
                    GameState object loaded from the file
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        gs = GameState()
        gs.resources = data.get('resources', {})
        pos = data.get('current_position', {})
        gs.current_position = (pos.get('x', 2), pos.get('y', 8))
        gs.items = data.get('items', {})
        gs.house = HouseMap.from_dict(data.get('house', {}))
        gs.current_room = Room.from_dict(data.get("current_room", {}))  #TODO: this might need to be specified
        gs.day = data.get("day", 1)
        gs.special_order = data.get("special_order", None)
        return gs