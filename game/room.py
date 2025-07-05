import time
from typing import Optional

import easyocr

from capture import parlor
from game.constants import DIRECTORY
from game.door import Door
from game.terminal import SecurityTerminal, LabTerminal, OfficeTerminal, ShelterTerminal
from utils import get_color_code


class Room:
    """
        Represents a room in the game with doors, items, and various properties

            Attributes:
                name: The name of the room in uppercase
                cost: The cost to draft this room
                type: List of room types (e.g., PERMANENT, BLUEPRINT)
                description: Detailed description of the room
                additional_info: Additional information about the room
                shape: The shape of the room (DEAD END, STRAIGHT, L, T, CROSS)
                doors: List of Door objects for this room
                position: Tuple of (x, y) coordinates
                trunks: Number of trunks in this room
                dig_spots: Number of dig spots in this room
                rarity: The rarity of this room type
                has_been_entered: Whether the player has entered this room
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False) -> None:
        """
            Initialize a Room instance

                Args:
                    name: The name of the room
                    cost: The cost to draft this room
                    type: List of room types
                    description: Detailed description of the room
                    additional_info: Additional information about the room
                    shape: The shape of the room
                    doors: List of Door objects for this room
                    position: Tuple of (x, y) coordinates
                    rarity: The rarity of this room type
                    trunks: Number of trunks in this room
                    dig_spots: Number of dig spots in this room
                    has_been_entered: Whether the player has entered this room
        """
        self.name = name.upper()
        self.cost = cost
        self.type = type if isinstance(type, list) else [type]
        self.description = description
        self.additional_info = additional_info
        self.shape = shape
        self.doors = doors if doors else []
        self.position = position
        self.trunks = trunks
        self.dig_spots = dig_spots
        self.rarity = rarity
        self.has_been_entered = has_been_entered

    @property
    def rank(self) -> int:
        """
            Calculate the rank of the room based on its position

                Returns:
                    The rank number (1-9)
        """
        return 9 - self.position[1]

    def edit_doors(self) -> None:
        """
            Interactive method to edit doors in this room
        """
        print(f"\n\n ----- DOOR EDITOR ----- \n")
        print(f"Editing DOORS for room: {get_color_code(self.name)}")
        while True:
            print("\nCurrent DOORS:")
            if self.doors:
                for door in self.doors:
                    print(door)
            else:
                print(f"No DOORS currently within {self.name}")

            print("\nOptions:")
            print("1. Edit a DOOR")
            print("2. Add a new DOOR")
            print("3. Remove a DOOR")
            print("4. Mark all DOORS as NOT SECURITY")
            print("\nq. Quit DOOR editing")

            choice = input("\n\nSelect an option: ").strip().lower()
            if choice == "1":
                self.edit_single_door_interactive()
            elif choice == "2":
                self.add_door_interactive()
            elif choice == "3":
                self.remove_door_interactive()
            elif choice == "4":
                for door in self.doors:
                    door.is_security = "False"
                print("\nAll DOORS marked as NOT SECURITY")
            elif choice == "q":
                print("\nExiting DOOR editor")
                break
            else:
                print("\nInvalid option")
                time.sleep(2)

    def edit_single_door_interactive(self) -> None:
        """
            Interactive method to edit a single door in this room
        """
        try:
            if not self.doors:
                print("\nNo DOORS to edit in this room.")
                time.sleep(2)
                return
            print("\nAvailable DOORS:")
            for door in (self.doors):
                print(door)
            door_orientation = input("Enter DOOR orientation to EDIT (N/S/E/W): ").strip().upper()
            matching_doors = [d for d in self.doors if d.orientation == door_orientation]
            if not matching_doors:
                print(f"\nNo DOOR with ORIENTATION {door_orientation} found.")
                time.sleep(2)
                return
            door = matching_doors[0]
            print(f"\nEditing DOOR: {door}")
            print("Fields you can edit: ORIENTATION, LOCKED, IS_SECURITY")
            field = input("Enter FIELD to EDIT: ").strip().lower()
            if field == "orientation":
                new_val = input(f"ORIENTATION [{door.orientation}]: ").strip().upper()
                if new_val:
                    door.orientation = new_val
            elif field == "locked":
                new_val = input(f"LOCKED (True/False) [{door.locked}]: ").strip()
                if new_val:
                    door.locked = str(new_val.lower() in ["true", "t", "yes", "y", "1"])
            elif field == "is_security":
                new_val = input(f"IS SECURITY (True/False) [{door.is_security}]: ").strip()
                if new_val:
                    door.is_security = str(new_val.lower() in ["true", "t", "yes", "y", "1"])
            else:
                print("\nInvalid field.")
                time.sleep(2)
                return
            print("DOOR updated.")
        except ValueError:
            print("\nInvalid input.")
            time.sleep(2)
            
    def add_door_interactive(self, count: int = 1) -> None:
        """
            Interactive method to add new doors to this room

                Args:
                    count: Number of doors to add
        """
        print(f"Adding {count} DOOR(s) to room: {self.name}")
        # TODO: add input validation for orientation, locked, is_security.. is in ["true", "t", "yes", "y", "1"]
        for i in range(count):
            orientation = input("ORIENTATION (N/S/E/W): ").strip().upper()
            locked = input("LOCKED (True/False/?) [?]: ").strip().lower()
            is_security = input("IS SECURITY (True/False/?) [?]: ").strip().lower()
            self.doors.append(Door(orientation=orientation, locked=locked, is_security=is_security))
            print(f"DOOR {i+1} added")

    def remove_door_interactive(self) -> None:
        """
            Interactive method to remove a door from this room
        """
        try:
            door_idx = int(input("Enter DOOR number to REMOVE: ")) - 1
            if 0 <= door_idx < len(self.doors):
                removed = self.doors.pop(door_idx)
                print(f"REMOVED DOOR: {removed}")
            else:
                print("\nInvalid DOOR number")
                time.sleep(2)
        except ValueError:
            print("\nInvalid INPUT")
            time.sleep(2)

    def get_door_by_orientation(self, door_dir: str) -> Door:
        """
            Get a door by its orientation

                Args:
                    door_dir: The direction of the door (N, S, E, W)

                Returns:
                    The Door object with the specified orientation

                Raises:
                    ValueError: If no door with the specified orientation is found
        """
        door = next((d for d in self.doors if getattr(d, "orientation", None) == door_dir), None)
        if not door:
            raise ValueError(f"DOOR '{door_dir}' not found in room '{self.name}'.")
        return door
    
    def get_door_count_from_shape(self) -> int:
        """
            Return the number of doors for a given room shape

                Returns:
                    The number of doors for the given shape
        """
        shape_to_door_count = {
            "DEAD END": 1,
            "STRAIGHT": 2,
            "L": 2,
            "T": 3,
            "CROSS": 4
        }
        
        return shape_to_door_count.get(self.shape.upper(), 0)  # default to 0 if shape not found
    
    def set_trunks(self) -> None:
        """
            Interactive method to set the number of trunks in this room
        """
        try:
            count = int(input("Enter the number of trunks in this room: ").strip())
            if count < 0:
                print("\nNumber cannot be negative.")
                time.sleep(2)
                return
            self.trunks = count
        except ValueError:
            print("\nInvalid input. Please enter a number.")
            time.sleep(2)

    def set_dig_spots(self) -> None:
        """
            Interactive method to set the number of dig spots in this room
        """
        try:
            count = int(input("Enter the number of dig spots in this room: ").strip())
            if count < 0:
                print("\nNumber cannot be negative.")
                time.sleep(2)
                return
            self.dig_spots = count
        except ValueError:
            print("\nInvalid input. Please enter a number.")
            time.sleep(2)

    def to_dict(self) -> dict:
        """
            Convert the Room instance to a dictionary representation

                Returns:
                    A dictionary representation of the room
        """
        return {
            "name": self.name,
            "cost": self.cost,
            "type": self.type,
            "description": self.description,
            "additional_info": self.additional_info,
            "shape": self.shape,
            "rank": self.rank,
            "doors": [door.to_dict() for door in self.doors],
            "position": self.position,
            "trunks": self.trunks,
            "dig_spots": self.dig_spots,
            "rarity": self.rarity,
            "has_been_entered": self.has_been_entered
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> 'Room':
        """
            Create a Room instance from a dictionary representation

                Args:
                    data: A dictionary containing room data
                    **kwargs: Additional keyword arguments

                Returns:
                    A Room instance created from the dictionary data
        """
        return cls(
            name=data.get("name", ""),
            cost=data.get("cost", 0),
            type=data.get("type", []),
            description=data.get("description", ""),
            additional_info=data.get("additional_info", ""),
            shape=data.get("shape", ""),
            doors=[Door.from_dict(door_data) for door_data in data.get("doors", [])],
            position=tuple(data["position"]),
            trunks=data.get("trunks", 0),
            dig_spots=data.get("dig_spots", 0),
            rarity=data.get("rarity", ""),
            has_been_entered=data.get("has_been_entered", False),
            **kwargs
        )
    
    def __str__(self) -> str:
        """
            Return a string representation of the Room

                Returns:
                    A string representation showing the room's properties
        """
        return f"Room(name={self.name}, cost={self.cost}, type={self.type}, description={self.description}, additional_info={self.additional_info}, shape={self.shape}, doors={self.doors}, position={self.position}, rank={self.rank}, trunks={self.trunks}, dig_spots={self.dig_spots}, rarity={self.rarity}, has_been_entered={self.has_been_entered})"


class ShopRoom(Room):
    """
        A specialized room where items can be purchased

            Attributes:
                items_for_sale: Dictionary of items available for purchase with their prices
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False, items_for_sale: Optional[dict] = None) -> None:
        """
            Initialize a ShopRoom instance

                Args:
                    name: The name of the room
                    cost: The cost to draft this room
                    type: List of room types
                    description: Detailed description of the room
                    additional_info: Additional information about the room
                    shape: The shape of the room
                    doors: List of Door objects for this room
                    position: Tuple of (x, y) coordinates
                    rarity: The rarity of this room type
                    trunks: Number of trunks in this room
                    dig_spots: Number of dig spots in this room
                    has_been_entered: Whether the player has entered this room
                    items_for_sale: Dictionary of items available for purchase
        """
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.items_for_sale = items_for_sale if items_for_sale else {}

    def edit_items_for_sale(self) -> None:
        """
            Interactive method to edit the items for sale in this shop room
        """
        while True:
            print(f"\nCurrent items for sale in {self.name}:")
            if not self.items_for_sale:
                print("  (No items currently for sale)")
            else:
                for item, price in self.items_for_sale.items():
                    print(f"  - {item}: {price}")

            print("\nOptions:")
            print("1. Add item")
            print("2. Remove item")
            print("3. Change item price")
            print("4. List all valid items")
            print("q. Quit editing items")

            choice = input("\n\nSelect an option: ").strip().lower()
            if choice == "1":
                item = input("Enter item name: ").strip().upper()
                # show suggestions if item not found
                if item not in DIRECTORY["ITEMS"]:
                    print("\nInvalid item name. Type '4' to list all valid items.")
                    time.sleep(2)
                    continue
                if item in self.items_for_sale:
                    print(f"\n{item} is already for sale. Use option 3 to change its price.")
                    time.sleep(2)
                    continue
                price = input("Enter item price: ").strip()
                if not price.isdigit() or int(price) < 0:
                    print("\nInvalid price. Please enter a non-negative number.")
                    time.sleep(2)
                    continue
                price = int(price)
                self.items_for_sale[item] = price
                print(f"\nAdded {item} for {price} coins.")
                time.sleep(1)
            elif choice == "2":
                item = input("Enter item name to remove: ").strip().upper()
                if item in self.items_for_sale:
                    confirm = input(f"Are you sure you want to remove {item}? (y/n): ").strip().lower()
                    if confirm == "y":
                        del self.items_for_sale[item]
                        print(f"\nRemoved {item}.")
                        time.sleep(1)
                    else:
                        print("\nRemoval cancelled.")
                        time.sleep(1)
                else:
                    print("\nItem not found in items for sale.")
                    time.sleep(2)
            elif choice == "3":
                item = input("Enter item name to change price: ").strip().upper()
                if item in self.items_for_sale:
                    price = input("Enter new price: ").strip()
                    if not price.isdigit() or int(price) < 0:
                        print("\nInvalid price. Please enter a non-negative number.")
                        time.sleep(2)
                        continue
                    price = int(price)
                    self.items_for_sale[item] = price
                    print(f"\nUpdated {item} price to {price} coins.")
                    time.sleep(1)
                else:
                    print("\nItem not found in items for sale.")
                    time.sleep(2)
            elif choice == "4":
                print("\nValid items:")
                for valid_item in sorted(DIRECTORY["ITEMS"].keys()):
                    print(f"  - {valid_item}")
                input("\nPress Enter to continue...")
            elif choice == "q":
                print("\nExiting item editor.")
                break
            else:
                print("\nInvalid option.")
                time.sleep(2)

    def to_dict(self) -> dict:
        """
            Convert the ShopRoom instance to a dictionary representation

                Returns:
                    A dictionary representation of the shop room
        """
        data = super().to_dict()
        data["items_for_sale"] = self.items_for_sale
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ShopRoom':
        """
            Create a ShopRoom instance from a dictionary representation

                Args:
                    data: A dictionary containing shop room data

                Returns:
                    A ShopRoom instance created from the dictionary data
        """
        items_for_sale = data.get("items_for_sale", {})
        return super().from_dict(data, items_for_sale=items_for_sale) # type: ignore
    
    def __str__(self) -> str:
        """
            Return a string representation of the ShopRoom

                Returns:
                    A string representation showing the shop room's properties
        """
        return super().__str__() + f", items_for_sale={self.items_for_sale})"


class PuzzleRoom(Room):
    """
        A specialized room containing puzzles that can be solved

            Attributes:
                has_been_solved: Whether the puzzle in this room has been solved
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False, has_been_solved: bool = False) -> None:
        """
            Initialize a PuzzleRoom instance

                Args:
                    name: The name of the room
                    cost: The cost to draft this room
                    type: List of room types
                    description: Detailed description of the room
                    additional_info: Additional information about the room
                    shape: The shape of the room
                    doors: List of Door objects for this room
                    position: Tuple of (x, y) coordinates
                    rarity: The rarity of this room type
                    trunks: Number of trunks in this room
                    dig_spots: Number of dig spots in this room
                    has_been_entered: Whether the player has entered this room
                    has_been_solved: Whether the puzzle has been solved
        """
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.has_been_solved = has_been_solved  # indicates if the puzzle in this room has been solved

    def parlor_puzzle(self, reader: easyocr.Reader, editor_path: Optional[str] = None) -> dict:
        """
            Interactive parlor puzzle solver

                Args:
                    reader: The OCR reader to capture text
                    editor_path: Path to text editor for manual editing

                Returns:
                    The results for each color box
        """
        colors = ["BLUE", "WHITE", "BLACK"]
        results = {}
        
        for color in colors:
            printable_box_color = get_color_code(color)
            while True:
                print(f"\nFor the {printable_box_color} box:")
                print("1. Capture with screenshot")
                print("2. Enter manually")
                
                capture_choice = input("Enter your choice (1/2): ").strip()
                
                if capture_choice == "1":
                    # screenshot capture path
                    input(f"Please get into position to screenshot the {printable_box_color} box, press Enter to continue...")
                    box_result = parlor.capture_hint(reader, editor_path)
                    print(f"OCR result for {printable_box_color} box: {box_result}")
                elif capture_choice == "2":
                    # manual entry path
                    box_result = input(f"\nEnter the text for the {printable_box_color} box: ").strip()
                else:
                    print("\nInvalid choice. Please enter 1 or 2.")
                    time.sleep(2)
                    continue
                
                confirm = input(f"Is the {printable_box_color} box result '{box_result}' correct? (Y/n): ").strip().lower()
                if confirm in ["y", "yes"]:
                    results[color] = box_result
                    break
                else:
                    print(f"Let's try again for the {printable_box_color} box.")
        return results
    
    def to_dict(self) -> dict:
        """
            Convert the PuzzleRoom instance to a dictionary representation

                Returns:
                    A dictionary representation of the puzzle room
        """
        data = super().to_dict()
        data["has_been_solved"] = self.has_been_solved
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PuzzleRoom':
        """
            Create a PuzzleRoom instance from a dictionary representation

                Args:
                    data: A dictionary containing puzzle room data

                Returns:
                    A PuzzleRoom instance created from the dictionary data
        """
        has_been_solved = data.get("has_been_solved", False)
        return super().from_dict(data, has_been_solved=has_been_solved) # type: ignore
    
    def __str__(self) -> str:
        """
            Return a string representation of the PuzzleRoom

                Returns:
                    A string representation showing the puzzle room's properties
        """
        return super().__str__() + f", has_been_solved={self.has_been_solved})"


class UtilityCloset(Room):
    """
        A utility closet containing various switches for different areas

            Attributes:
                keycard_entry_system_switch: State of the keycard system switch
                gymnasium_switch: State of the gymnasium switch
                darkroom_switch: State of the darkroom switch
                garage_switch: State of the garage switch
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False, keycard_entry_system_switch: bool = True, gymnasium_switch: bool = True, darkroom_switch: bool = False, garage_switch: bool = False) -> None:
        """
            Initialize a UtilityCloset instance

                Args:
                    name: The name of the room
                    cost: The cost to draft this room
                    type: List of room types
                    description: Detailed description of the room
                    additional_info: Additional information about the room
                    shape: The shape of the room
                    doors: List of Door objects for this room
                    position: Tuple of (x, y) coordinates
                    rarity: The rarity of this room type
                    trunks: Number of trunks in this room
                    dig_spots: Number of dig spots in this room
                    has_been_entered: Whether the player has entered this room
                    keycard_entry_system_switch: State of the keycard system switch
                    gymnasium_switch: State of the gymnasium switch
                    darkroom_switch: State of the darkroom switch
                    garage_switch: State of the garage switch
        """
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.keycard_entry_system_switch = keycard_entry_system_switch
        self.gymnasium_switch = gymnasium_switch
        self.darkroom_switch = darkroom_switch
        self.garage_switch = garage_switch

    def toggle_switch(self, switch_name: str) -> None:
        """
            Toggle the state of a specific switch in the utility closet

                Args:
                    switch_name: The name of the switch to toggle
        """
        if hasattr(self, switch_name):
            current_state = getattr(self, switch_name)
            if isinstance(current_state, bool):
                new_state = not current_state    # flip the boolean value
                setattr(self, switch_name, new_state)
                print(f"Set {switch_name} to {new_state}.")
            else:
                print(f"Switch {switch_name} is not a boolean.")
        else:
            print(f"Switch {switch_name} does not exist.")

    def to_dict(self) -> dict:
        """
            Convert the UtilityCloset instance to a dictionary representation

                Returns:
                    A dictionary representation of the utility closet
        """
        data = super().to_dict()
        data["keycard_entry_system_switch"] = self.keycard_entry_system_switch
        data["gymnasium_switch"] = self.gymnasium_switch
        data["darkroom_switch"] = self.darkroom_switch
        data["garage_switch"] = self.garage_switch
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UtilityCloset':
        """
            Create a UtilityCloset instance from a dictionary representation

                Args:
                    data: A dictionary containing utility closet data

                Returns:
                    A UtilityCloset instance created from the dictionary data
        """
        base_room = super().from_dict(data)                         # get the base room attributes
        base_data = {k: v for k, v in base_room.to_dict().items() if k not in ["doors", "rank"]}  # remove the doors from the base room attributes
        utility_closet = cls(**base_data, doors=base_room.doors)         # create the utility closet with the base room attributes
        utility_closet.keycard_entry_system_switch = data.get("keycard_entry_system_switch", True)  # add the keycard entry system switch attribute to the utility closet
        utility_closet.gymnasium_switch = data.get("gymnasium_switch", True)  # add the gymnasium switch attribute to the utility closet
        utility_closet.darkroom_switch = data.get("darkroom_switch", False)  # add the darkroom switch attribute to the utility closet
        utility_closet.garage_switch = data.get("garage_switch", False)  # add the garage switch attribute to the utility closet
        return utility_closet
    
    def __str__(self) -> str:
        """
            Return a string representation of the UtilityCloset

                Returns:
                    A string representation showing the utility closet's properties
        """
        return super().__str__() + f", keycard_entry_system_switch={self.keycard_entry_system_switch}, gymnasium_switch={self.gymnasium_switch}, darkroom_switch={self.darkroom_switch}, garage_switch={self.garage_switch})"


class CoatCheck(Room):
    """
        A room that allows the player to store and retrieve an item across runs

            Attributes:
                stored_item: The item currently stored in the coat check
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False, stored_item: str = "") -> None:
        """
            Initialize a CoatCheck instance

                Args:
                    name: The name of the room
                    cost: The cost to draft this room
                    type: List of room types
                    description: Detailed description of the room
                    additional_info: Additional information about the room
                    shape: The shape of the room
                    doors: List of Door objects for this room
                    position: Tuple of (x, y) coordinates
                    rarity: The rarity of this room type
                    trunks: Number of trunks in this room
                    dig_spots: Number of dig spots in this room
                    has_been_entered: Whether the player has entered this room
                    stored_item: The item currently stored in the coat check
        """
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.stored_item = stored_item

    def store_item(self, item: str) -> None:
        """
            Store an item in the coat check

                Args:
                    item: The item to store
        """
        self.stored_item = item

    def retrieve_item(self) -> str:
        """
            Retrieve the stored item from the coat check

                Returns:
                    The previously stored item (empty string after retrieval)
        """
        self.stored_item = ""
        return self.stored_item
    
    def to_dict(self) -> dict:
        """
            Convert the CoatCheck instance to a dictionary representation

                Returns:
                    A dictionary representation of the coat check
        """
        data = super().to_dict()
        data["stored_item"] = self.stored_item
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'CoatCheck':
        """
            Create a CoatCheck instance from a dictionary representation

                Args:
                    data: A dictionary containing coat check data

                Returns:
                    A CoatCheck instance created from the dictionary data
        """
        stored_item = data.get("stored_item", "")
        return super().from_dict(data, stored_item=stored_item) # type: ignore

    def __str__(self) -> str:
        """
            Return a string representation of the CoatCheck

                Returns:
                    A string representation showing the coat check's properties
        """
        return super().__str__() + f", stored_item={self.stored_item})"
    
# class Library(Room):
#     """
#         Represents a library room with bookshelves
#     """
#     def __init__(self, name="", cost=0, type=[], description="", additional_info="", shape="", doors=None, position=None, rank=0, trunks=0, dig_spots=0, rarity="", has_been_entered=False, terminal: Optional[Union[Terminal, SecurityTerminal, LabTerminal, OfficeTerminal, ShelterTerminal]] = None, avialable_books=None):
#         super().__init__(name, cost, type, description, additional_info, shape, doors, position, rank, trunks, dig_spots, rarity, has_been_entered, terminal)
#         self.available_books = avialable_books if avialable_books is not None else []
        

#     def to_dict(self):
#         return super().to_dict()
    
#     @classmethod
#     def from_dict(cls, data):
#         return super().from_dict(data)
    
#     def __str__(self):
#         return super().__str__()


class SecretPassage(Room):
    """
        A room representing a secret passage with a hidden door

            Attributes:
                has_been_used: Whether the secret passage has been used
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False, has_been_used: bool = False) -> None:
        """
            Initialize a SecretPassage instance

                Args:
                    name: The name of the room
                    cost: The cost to draft this room
                    type: List of room types
                    description: Detailed description of the room
                    additional_info: Additional information about the room
                    shape: The shape of the room
                    doors: List of Door objects for this room
                    position: Tuple of (x, y) coordinates
                    rarity: The rarity of this room type
                    trunks: Number of trunks in this room
                    dig_spots: Number of dig spots in this room
                    has_been_entered: Whether the player has entered this room
                    has_been_used: Whether the secret passage has been used
        """
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.has_been_used = has_been_used

    def to_dict(self) -> dict:
        """
            Convert the SecretPassage instance to a dictionary representation

                Returns:
                    A dictionary representation of the secret passage
        """
        data = super().to_dict()
        data["has_been_used"] = self.has_been_used
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SecretPassage':
        """
            Create a SecretPassage instance from a dictionary representation

                Args:
                    data: A dictionary containing secret passage data

                Returns:
                    A SecretPassage instance created from the dictionary data
        """
        has_been_used = data.get("has_been_used", False)
        return super().from_dict(data, has_been_used=has_been_used) # type: ignore
    
    def __str__(self) -> str:
        """
            Return a string representation of the SecretPassage

                Returns:
                    A string representation showing the secret passage's properties
        """
        return super().__str__()


class Security(Room):
    """
        A room representing a security room with a terminal

            Attributes:
                terminal: The SecurityTerminal instance for this room
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, terminal: SecurityTerminal, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False) -> None:
        """
            Initialize a Security instance

                Args:
                    name: The name of the room
                    cost: The cost to draft this room
                    type: List of room types
                    description: Detailed description of the room
                    additional_info: Additional information about the room
                    shape: The shape of the room
                    doors: List of Door objects for this room
                    position: Tuple of (x, y) coordinates
                    rarity: The rarity of this room type
                    terminal: The SecurityTerminal instance for this room
                    trunks: Number of trunks in this room
                    dig_spots: Number of dig spots in this room
                    has_been_entered: Whether the player has entered this room
        """
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.terminal = terminal

    def to_dict(self) -> dict:
        """
            Convert the Security instance to a dictionary representation

                Returns:
                    A dictionary representation of the security room
        """
        data = super().to_dict()
        data["terminal"] = self.terminal.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Security':
        """
            Create a Security instance from a dictionary representation

                Args:
                    data: A dictionary containing security room data

                Returns:
                    A Security instance created from the dictionary data
        """
        # handle missing or invalid terminal data
        terminal_data = data.get("terminal")
        if terminal_data:
            terminal = SecurityTerminal.from_dict(terminal_data)
        else:
            terminal = SecurityTerminal()  # create default terminal
        
        return super().from_dict(data, terminal=terminal) # type: ignore
    
    def __str__(self) -> str:
        """
            Return a string representation of the Security

                Returns:
                    A string representation showing the security room's properties
        """
        return super().__str__() + f", terminal={self.terminal})"


class Office(Room):
    """
        A room representing an office with a terminal

            Attributes:
                terminal: The OfficeTerminal instance for this room
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, terminal: OfficeTerminal, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False) -> None:
        """
            Initialize an Office instance

                Args:
                    name: The name of the room
                    cost: The cost to draft this room
                    type: List of room types
                    description: Detailed description of the room
                    additional_info: Additional information about the room
                    shape: The shape of the room
                    doors: List of Door objects for this room
                    position: Tuple of (x, y) coordinates
                    rarity: The rarity of this room type
                    terminal: The OfficeTerminal instance for this room
                    trunks: Number of trunks in this room
                    dig_spots: Number of dig spots in this room
                    has_been_entered: Whether the player has entered this room
        """
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.terminal = terminal

    def to_dict(self) -> dict:
        """
            Convert the Office instance to a dictionary representation

                Returns:
                    A dictionary representation of the office room
        """
        data = super().to_dict()
        data["terminal"] = self.terminal.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Office':
        """
            Create an Office instance from a dictionary representation

                Args:
                    data: A dictionary containing office room data

                Returns:
                    An Office instance created from the dictionary data
        """
        # handle terminal creation
        terminal_data = data.get("terminal")
        if terminal_data and isinstance(terminal_data, dict):
            terminal = OfficeTerminal.from_dict(terminal_data)
        else:
            terminal = OfficeTerminal()  # create default terminal
        
        # Create base room, passing the terminal as an extra argument
        return super().from_dict(data, terminal=terminal) # type: ignore
    
    def __str__(self) -> str:
        """
            Return a string representation of the Office

                Returns:
                    A string representation showing the office room's properties
        """
        return super().__str__() + f", terminal={self.terminal})"


class Laboratory(Room):
    """
        A room representing a laboratory with a terminal

            Attributes:
                terminal: The LabTerminal instance for this room
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, terminal: LabTerminal, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False) -> None:
        """
            Initialize a Laboratory instance

                Args:
                    name: The name of the room
                    cost: The cost to draft this room
                    type: List of room types
                    description: Detailed description of the room
                    additional_info: Additional information about the room
                    shape: The shape of the room
                    doors: List of Door objects for this room
                    position: Tuple of (x, y) coordinates
                    rarity: The rarity of this room type
                    terminal: The LabTerminal instance for this room
                    trunks: Number of trunks in this room
                    dig_spots: Number of dig spots in this room
                    has_been_entered: Whether the player has entered this room
        """
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.terminal = terminal

    def to_dict(self) -> dict:
        """
            Convert the Laboratory instance to a dictionary representation

                Returns:
                    A dictionary representation of the laboratory room
        """
        data = super().to_dict()
        data["terminal"] = self.terminal.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Laboratory':
        """
            Create a Laboratory instance from a dictionary representation

                Args:
                    data: A dictionary containing laboratory room data

                Returns:
                    A Laboratory instance created from the dictionary data
        """
        # handle missing or invalid terminal data
        terminal_data = data.get("terminal")
        if terminal_data:
            terminal = LabTerminal.from_dict(terminal_data)
        else:
            terminal = LabTerminal()  # create default terminal
        
        return super().from_dict(data, terminal=terminal) # type: ignore
    
    def __str__(self) -> str:
        """
            Return a string representation of the Laboratory

                Returns:
                    A string representation showing the laboratory room's properties
        """
        return super().__str__() + f", terminal={self.terminal})"


class Shelter(Room):
    """
        A room representing a shelter with a terminal

            Attributes:
                terminal: The ShelterTerminal instance for this room
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, terminal: ShelterTerminal, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False) -> None:
        """
            Initialize a Shelter instance

                Args:
                    name: The name of the room
                    cost: The cost to draft this room
                    type: List of room types
                    description: Detailed description of the room
                    additional_info: Additional information about the room
                    shape: The shape of the room
                    doors: List of Door objects for this room
                    position: Tuple of (x, y) coordinates
                    rarity: The rarity of this room type
                    terminal: The ShelterTerminal instance for this room
                    trunks: Number of trunks in this room
                    dig_spots: Number of dig spots in this room
                    has_been_entered: Whether the player has entered this room
        """
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.terminal = terminal

    def to_dict(self) -> dict:
        """
            Convert the Shelter instance to a dictionary representation

                Returns:
                    A dictionary representation of the shelter room
        """
        data = super().to_dict()
        data["terminal"] = self.terminal.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Shelter':
        """
            Create a Shelter instance from a dictionary representation

                Args:
                    data: A dictionary containing shelter room data

                Returns:
                    A Shelter instance created from the dictionary data
        """
        # handle missing or invalid terminal data
        terminal_data = data.get("terminal")
        if terminal_data:
            terminal = ShelterTerminal.from_dict(terminal_data)
        else:
            terminal = ShelterTerminal()  # Create default terminal
        
        return super().from_dict(data, terminal=terminal) # type: ignore
    
    def __str__(self):
        return super().__str__() + f", terminal={self.terminal})"





