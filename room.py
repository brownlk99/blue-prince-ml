import time
from typing import Optional, Union
import easyocr
from capture import parlor
from door import Door
from terminal import Terminal, SecurityTerminal, LabTerminal, OfficeTerminal, ShelterTerminal

from capture.constants import DIRECTORY
from utils import get_color_code


class Room:
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False):
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
    def rank(self):
        return 9 - self.position[1]

    def edit_doors(self):
        print(f"\n\n ----- DOOR EDITOR ----- \n")
        print(f"Editing doors for room: {get_color_code(self.name)}")
        while True:
            print("\nCurrent DOORS:")
            if self.doors:
                for door in self.doors:
                    print(door)
            else:
                print(f"No doors currently within {self.name}")

            print("\nOptions:")
            print("1. Edit a door")
            print("2. Add a new door")
            print("3. Remove a door")
            print("4. Mark all doors as not security")
            print("\nq. Quit door editing")

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
                print("\nAll doors marked as not security.")
            elif choice == "q":
                print("\nExiting door editor.")
                break
            else:
                print("\nInvalid option.")
                time.sleep(3)

    def edit_single_door_interactive(self):
        try:
            if not self.doors:
                print("\nNo doors to edit in this room.")
                time.sleep(3)
                return
            print("\nAvailable doors:")
            for door in (self.doors):
                print(door)
            door_orientation = input("Enter door orientation to edit (N/S/E/W): ").strip().upper()
            matching_doors = [d for d in self.doors if d.orientation == door_orientation]
            if not matching_doors:
                print(f"\nNo door with orientation {door_orientation} found.")
                time.sleep(3)
                return
            door = matching_doors[0]
            print(f"\nEditing DOOR: {door}")
            print("Fields you can edit: orientation, locked, is_security")
            field = input("Enter field to edit: ").strip().lower()
            if field == "orientation":
                new_val = input(f"Orientation [{door.orientation}]: ").strip().upper()
                if new_val:
                    door.orientation = new_val
            elif field == "locked":
                new_val = input(f"Locked (True/False) [{door.locked}]: ").strip()
                if new_val:
                    door.locked = str(new_val.lower() in ["true", "t", "yes", "y", "1"])
            elif field == "is_security":
                new_val = input(f"Is Security (True/False) [{door.is_security}]: ").strip()
                if new_val:
                    door.is_security = str(new_val.lower() in ["true", "t", "yes", "y", "1"])
            else:
                print("\nInvalid field.")
                time.sleep(3)
                return
            print("Door updated.")
        except ValueError:
            print("\nInvalid input.")
            time.sleep(3)
            
    def add_door_interactive(self, count: int = 1) -> None:
        print(f"Adding {count} door(s) to room: {self.name}")
        #TODO: add input validation for orientation, locked, is_security.. is in ["true", "t", "yes", "y", "1"]
        for i in range(count):
            orientation = input("Orientation (N/S/E/W): ").strip().upper()
            locked = input("Locked (True/False) [False]: ").strip().lower()
            is_security = input("Is Security (True/False) [False]: ").strip().lower()
            self.doors.append(Door(orientation=orientation, locked=locked, is_security=is_security))
            print(f"Door {i+1} added.")

    def remove_door_interactive(self):
        try:
            door_idx = int(input("Enter door number to remove: ")) - 1
            if 0 <= door_idx < len(self.doors):
                removed = self.doors.pop(door_idx)
                print(f"Removed door: {removed}")
            else:
                print("\nInvalid door number.")
                time.sleep(3)
        except ValueError:
            print("\nInvalid input.")
            time.sleep(3)

    def get_door_by_orientation(self, door_dir):
        door = next((d for d in self.doors if getattr(d, "orientation", None) == door_dir), None)
        if not door:
            raise ValueError(f"Door '{door_dir}' not found in room '{self.name}'.")
        return door
    
    def get_door_count_from_shape(self):
        """
            returns the number of doors for a given room shape

                Args:
                    shape (str): the shape of the room (DEAD END, STRAIGHT, L, T, CROSS)

                Returns:
                    int: the number of doors for the given shape
        """
        shape_to_door_count = {
            "DEAD END": 1,
            "STRAIGHT": 2,
            "L": 2,
            "T": 3,
            "CROSS": 4
        }
        
        return shape_to_door_count.get(self.shape.upper(), 0)  # default to 0 if shape not found
    
    def set_trunks(self):
        try:
            count = int(input("Enter the number of trunks in this room: ").strip())
            if count < 0:
                print("\nNumber cannot be negative.")
                time.sleep(3)
                return
            self.trunks = count
            print(f"Set {count} trunks in this room.")
        except ValueError:
            print("\nInvalid input. Please enter a number.")
            time.sleep(3)

    def set_dig_spots(self):
        try:
            count = int(input("Enter the number of dig spots in this room: ").strip())
            if count < 0:
                print("\nNumber cannot be negative.")
                time.sleep(3)
                return
            self.dig_spots = count
            print(f"Set {count} dig spots in this room.")
        except ValueError:
            print("\nInvalid input. Please enter a number.")
            time.sleep(3)


    def to_dict(self):
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
    def from_dict(cls, data):
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
            has_been_entered=data.get("has_been_entered", "False")
        )
    
    def __str__(self):
        return f"Room(name={self.name}, cost={self.cost}, type={self.type}, description={self.description}, additional_info={self.additional_info}, shape={self.shape}, doors={self.doors}, position={self.position}, rank={self.rank}, trunks={self.trunks}, dig_spots={self.dig_spots}, rarity={self.rarity}, has_been_entered={self.has_been_entered})"

class ShopRoom(Room):
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False, items_for_sale: Optional[dict] = None):
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.items_for_sale = items_for_sale if items_for_sale else {}

    def edit_items_for_sale(self):
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
                # Show suggestions if item not found
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

    def to_dict(self):
        data = super().to_dict()
        data["items_for_sale"] = self.items_for_sale
        return data
    
    @classmethod
    def from_dict(cls, data):
        #TODO: maybe pop the doors from the data and then add them back onto the shop room.. instead of going from dict to to dict OR just do it the long way
        base_room = super().from_dict(data)                         #get the base room attributes
        base_data = {k: v for k, v in base_room.to_dict().items() if k not in ["doors", "rank"]}  #remove the doors from the base room attributes
        shop_room = cls(**base_data, doors=base_room.doors)         #create the shop room with the base room attributes
        shop_room.items_for_sale = data.get("items_for_sale", {})   #add the items for sale into the shop room
        return shop_room
    
    def __str__(self):
        return super().__str__() + f", items_for_sale={self.items_for_sale})"

class PuzzleRoom(Room):
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False, has_been_solved: bool = False):
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.has_been_solved = has_been_solved  # Indicates if the puzzle in this room has been solved

    def parlor_puzzle(self, reader: easyocr.Reader, editor_path: Optional[str] = None):
        """
            interactive parlor puzzle solver

                Args:
                    reader (easyocr.Reader): the OCR reader to capture text
                    editor_path (str): path to text editor for manual editing

                Returns:
                    dict: the results for each color box
        """
        colors = ["BLUE", "WHITE", "BLACK"]
        results = {}
        
        for color in colors:
            while True:
                print(f"\nFor the {color} box:")
                print("1. Capture with screenshot")
                print("2. Enter manually")
                
                capture_choice = input("\n\nEnter your choice (1/2): ").strip()
                
                if capture_choice == "1":
                    # Screenshot capture path
                    input(f"Please get into position to screenshot the {color} box, press Enter to continue...")
                    box_result = parlor.capture_hint(reader, editor_path)
                    print(f"OCR result for {color} box: {box_result}")
                elif capture_choice == "2":
                    # Manual entry path
                    box_result = input(f"\nEnter the text for the {color} box: ").strip()
                else:
                    print("\nInvalid choice. Please enter 1 or 2.")
                    time.sleep(3)
                    continue
                
                confirm = input(f"Is the {color} box result '{box_result}' correct? (Y/n): ").strip().lower()
                if confirm in ["y", "yes"]:
                    results[color] = box_result
                    break
                else:
                    print(f"Let's try again for the {color} box.")
        
        return results
    
    def to_dict(self):
        data = super().to_dict()
        data["has_been_solved"] = self.has_been_solved
        return data
    
    @classmethod
    def from_dict(cls, data):
        base_room = super().from_dict(data)                         #get the base room attributes
        base_data = {k: v for k, v in base_room.to_dict().items() if k not in ["doors", "rank"]}  #remove the doors from the base room attributes
        puzzle_room = cls(**base_data, doors=base_room.doors)         #create the puzzle room with the base room attributes
        puzzle_room.has_been_solved = data.get("has_been_solved", False)  #add the has been solved attribute to the puzzle room
        return puzzle_room
    
    def __str__(self):
        return super().__str__() + f", has_been_solved={self.has_been_solved})"

class UtilityCloset(Room):
    """
        A utility closet containing various switches for different areas.

            Args: True means on, False means off
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False, keycard_entry_system_switch: bool = True, gymnasium_switch: bool = True, darkroom_switch: bool = False, garage_switch: bool = False):
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.keycard_entry_system_switch = keycard_entry_system_switch
        self.gymnasium_switch = gymnasium_switch
        self.darkroom_switch = darkroom_switch
        self.garage_switch = garage_switch

    def toggle_switch(self, switch_name: str) -> None:
        """
            toggles the state of a specific switch in the utility closet

                Args:
                    switch_name (str): the name of the switch to toggle

                Returns:
                    None
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

    def to_dict(self):
        data = super().to_dict()
        data["keycard_entry_system_switch"] = self.keycard_entry_system_switch
        data["gymnasium_switch"] = self.gymnasium_switch
        data["darkroom_switch"] = self.darkroom_switch
        data["garage_switch"] = self.garage_switch
        return data
    
    @classmethod
    def from_dict(cls, data):
        base_room = super().from_dict(data)                         #get the base room attributes
        base_data = {k: v for k, v in base_room.to_dict().items() if k not in ["doors", "rank"]}  #remove the doors from the base room attributes
        utility_closet = cls(**base_data, doors=base_room.doors)         #create the utility closet with the base room attributes
        utility_closet.keycard_entry_system_switch = data.get("keycard_entry_system_switch", True)  #add the keycard entry system switch attribute to the utility closet
        utility_closet.gymnasium_switch = data.get("gymnasium_switch", True)  #add the gymnasium switch attribute to the utility closet
        utility_closet.darkroom_switch = data.get("darkroom_switch", False)  #add the darkroom switch attribute to the utility closet
        utility_closet.garage_switch = data.get("garage_switch", False)  #add the garage switch attribute to the utility closet
        return utility_closet
    
    def __str__(self):
        return super().__str__() + f", keycard_entry_system_switch={self.keycard_entry_system_switch}, gymnasium_switch={self.gymnasium_switch}, darkroom_switch={self.darkroom_switch}, garage_switch={self.garage_switch})"
    
class CoatCheck(Room):
    """
        Allows the player to store and retrieve an item across runs
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False, stored_item: str = ""):
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.stored_item = stored_item

    def store_item(self, item: str):
        self.stored_item = item

    def retrieve_item(self) -> str:
        self.stored_item = ""
        return self.stored_item
    
    def to_dict(self):
        data = super().to_dict()
        data["stored_item"] = self.stored_item
        return data

    @classmethod
    def from_dict(cls, data):
        base_room = super().from_dict(data)                         #get the base room attributes
        base_data = {k: v for k, v in base_room.to_dict().items() if k not in ["doors", "rank"]}  #remove the doors from the base room attributes
        coat_check = cls(**base_data, doors=base_room.doors)         #create the coat check with the base room attributes
        coat_check.stored_item = data.get("stored_item")             #add the stored item attribute to the coat check
        return coat_check

    def __str__(self):
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
        Represents a secret passage room with a hidden door
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False, has_been_used: bool = False):
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.has_been_used = has_been_used

    def to_dict(self):
        data = super().to_dict()
        data["has_been_used"] = self.has_been_used
        return data
    
    @classmethod
    def from_dict(cls, data):
        base_room = super().from_dict(data)
        base_data = {k: v for k, v in base_room.to_dict().items() if k not in ["doors", "rank"]}
        secret_passage = cls(**base_data, doors=base_room.doors)
        secret_passage.has_been_used = data.get("has_been_used", False)
        return secret_passage
    
    def __str__(self):
        return super().__str__()


class Security(Room):
    """
        Represents a security room with a terminal
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, terminal: SecurityTerminal,trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False):
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.terminal = terminal

    def to_dict(self):
        data = super().to_dict()
        data["terminal"] = self.terminal.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data):
        base_room = super().from_dict(data)
        base_data = {k: v for k, v in base_room.to_dict().items() if k not in ["doors", "rank"]}
        
        # Handle missing or invalid terminal data
        terminal_data = data.get("terminal")
        if terminal_data:
            terminal = SecurityTerminal.from_dict(terminal_data)
        else:
            terminal = SecurityTerminal()  # Create default terminal
        
        security = cls(**base_data, doors=base_room.doors, terminal=terminal)
        return security
    
    def __str__(self):
        return super().__str__() + f", terminal={self.terminal})"

class Office(Room):
    """
        Represents an office room with a terminal
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, terminal: OfficeTerminal, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False):
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.terminal = terminal

    def to_dict(self):
        data = super().to_dict()
        data["terminal"] = self.terminal.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data):
        base_room = super().from_dict(data)
        base_data = {k: v for k, v in base_room.to_dict().items() if k not in ["doors", "rank"]}
        
        # Handle missing or invalid terminal data
        terminal_data = data.get("terminal")
        if terminal_data:
            terminal = OfficeTerminal.from_dict(terminal_data)
        else:
            terminal = OfficeTerminal()  # Create default terminal
        
        office = cls(**base_data, doors=base_room.doors, terminal=terminal)
        return office
    
    def __str__(self):
        return super().__str__() + f", terminal={self.terminal})"

class Laboratory(Room):
    """
        Represents a laboratory room with a terminal
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, terminal: LabTerminal, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False):
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.terminal = terminal

    def to_dict(self):
        data = super().to_dict()
        data["terminal"] = self.terminal.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data):
        base_room = super().from_dict(data)
        base_data = {k: v for k, v in base_room.to_dict().items() if k not in ["doors", "rank"]}
        
        # Handle missing or invalid terminal data
        terminal_data = data.get("terminal")
        if terminal_data:
            terminal = LabTerminal.from_dict(terminal_data)
        else:
            terminal = LabTerminal()  # Create default terminal
        
        laboratory = cls(**base_data, doors=base_room.doors, terminal=terminal)
        return laboratory
    
    def __str__(self):
        return super().__str__() + f", terminal={self.terminal})"

class Shelter(Room):
    """
        Represents a shelter room with a terminal
    """
    def __init__(self, name: str, cost: int, type: list[str], description: str, additional_info: str, shape: str, doors: list[Door], position: tuple, rarity: str, terminal: ShelterTerminal, trunks: int = 0, dig_spots: int = 0, has_been_entered: bool = False):
        super().__init__(name, cost, type, description, additional_info, shape, doors, position, rarity, trunks, dig_spots, has_been_entered)
        self.terminal = terminal

    def to_dict(self):
        data = super().to_dict()
        data["terminal"] = self.terminal.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data):
        base_room = super().from_dict(data)
        base_data = {k: v for k, v in base_room.to_dict().items() if k not in ["doors", "rank"]}
        
        # Handle missing or invalid terminal data
        terminal_data = data.get("terminal")
        if terminal_data:
            terminal = ShelterTerminal.from_dict(terminal_data)
        else:
            terminal = ShelterTerminal()  # Create default terminal
        
        shelter = cls(**base_data, doors=base_room.doors, terminal=terminal)
        return shelter
    
    def __str__(self):
        return super().__str__() + f", terminal={self.terminal})"





