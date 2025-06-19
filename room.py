import time
from typing import Optional, Union
import easyocr
from capture import parlor
from door import Door
from terminal import Terminal, SecurityTerminal, LabTerminal, OfficeTerminal, ShelterTerminal

from capture.constants import DIRECTORY


class Room:
    def __init__(self, name="", cost=0, room_type="", description="", additional_info="", shape="", doors=None, position=None, rank=0, trunks=0, dig_spots=0, rarity="", has_been_entered=False, terminal: Optional[Union[Terminal, SecurityTerminal, LabTerminal, OfficeTerminal, ShelterTerminal]] = None):
        self.name = name.upper()
        self.cost = cost
        self.type = room_type  # could be list or string
        self.description = description
        self.additional_info = additional_info
        self.shape = shape
        self.doors = doors if doors else []
        self.position = position  # tuple like (x, y)
        self.rank = 9 - position[1] if position else None
        self.trunks = trunks
        self.dig_spots = dig_spots
        self.rarity = rarity
        self.has_been_entered = has_been_entered
        self.terminal = terminal

    def edit_doors(self):
        print(f"\nEditing doors for room: {self.name}")
        while True:
            print("\nCurrent doors:")
            for idx, door in enumerate(self.doors):
                print(f"{idx+1}: {door}")

            print("\nOptions:")
            print("1. Edit a door")
            print("2. Add a new door")
            print("3. Remove a door")
            print("4. Mark all doors as not security")
            print("q. Quit door editing")

            choice = input("Select an option: ").strip().lower()
            if choice == "1":
                self.edit_single_door_interactive()
            elif choice == "2":
                self.add_door_interactive()
            elif choice == "3":
                self.remove_door_interactive()
            elif choice == "4":
                for door in self.doors:
                    door.is_security = "False"
                print("All doors marked as not security.")
            elif choice == "q":
                print("Exiting door editor.")
                break
            else:
                print("Invalid option.")

    def edit_single_door_interactive(self): # not really any input validation but useful for manual corrections
        try:
            door_idx = int(input("Enter door number to edit: ")) - 1
            if 0 <= door_idx < len(self.doors):
                door = self.doors[door_idx]
                print(f"Editing door: {door}")
                print("Fields you can edit: orientation, locked, is_security, discovered")
                field = input("Enter field to edit: ").strip().lower()
                if field == "orientation":
                    new_val = input(f"Orientation [{door.orientation}]: ").strip().upper()
                    if new_val:
                        door.orientation = new_val
                elif field == "locked":
                    new_val = input(f"Locked (True/False) [{door.locked}]: ").strip()
                    if new_val:
                        door.locked = new_val.lower() == "true"
                elif field == "is_security":
                    new_val = input(f"Is Security (True/False) [{door.is_security}]: ").strip()
                    if new_val:
                        door.is_security = new_val.lower() == "true"
                else:
                    print("Invalid field.")
                print("Door updated.")
            else:
                print("Invalid door number.")
        except ValueError:
            print("Invalid input.")
            
    def add_door_interactive(self):
        orientation = input("Orientation (N/S/E/W): ").strip().upper()
        locked = input("Locked (True/False) [False]: ").strip().lower()
        is_security = input("Is Security (True/False) [False]: ").strip().lower()
        self.doors.append(Door(orientation=orientation, locked=locked, is_security=is_security))
        print("Door added.")

    def remove_door_interactive(self):
        try:
            door_idx = int(input("Enter door number to remove: ")) - 1
            if 0 <= door_idx < len(self.doors):
                removed = self.doors.pop(door_idx)
                print(f"Removed door: {removed}")
            else:
                print("Invalid door number.")
        except ValueError:
            print("Invalid input.")

    def get_door_by_orientation(self, door_dir):
        door = next((d for d in self.doors if getattr(d, "orientation", None) == door_dir), None)
        if not door:
            raise ValueError(f"Door '{door_dir}' not found in room '{self.name}'.")
        return door
    
    def set_trunks(self):
        try:
            count = int(input("Enter the number of trunks in this room: ").strip())
            if count < 0:
                print("Number cannot be negative.")
                return
            self.trunks = count
            print(f"Set {count} trunks in this room.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    def set_dig_spots(self):
        try:
            count = int(input("Enter the number of dig spots in this room: ").strip())
            if count < 0:
                print("Number cannot be negative.")
                return
            self.dig_spots = count
            print(f"Set {count} dig spots in this room.")
        except ValueError:
            print("Invalid input. Please enter a number.")


    def to_dict(self):
        return {
            "name": self.name,
            "cost": self.cost,
            "type": self.type,
            "description": self.description,
            "additional_info": self.additional_info,
            "shape": self.shape,
            "doors": [door.to_dict() for door in self.doors],
            "position": self.position,
            "rank": self.rank,
            "trunks": self.trunks,
            "dig_spots": self.dig_spots,
            "rarity": self.rarity,
            "has_been_entered": self.has_been_entered,
            "terminal": self.terminal
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get("name", ""),
            cost=data.get("cost", 0),
            room_type=data.get("type", ""),
            description=data.get("description", ""),
            additional_info=data.get("additional_info", ""),
            shape=data.get("shape", ""),
            doors=[Door.from_dict(door_data) for door_data in data.get("doors", [])],
            position=tuple(data["position"]) if "position" in data else None,
            rank=data.get("rank", 0),
            trunks=data.get("trunks", 0),
            dig_spots=data.get("dig_spots", 0),
            rarity=data.get("rarity", ""),
            has_been_entered=data.get("has_been_entered", "False"),
            terminal=data.get("terminal", None)
        )
    
    def __str__(self):
        return f"Room(name={self.name}, cost={self.cost}, type={self.type}, description={self.description}, additional_info={self.additional_info}, shape={self.shape}, doors={self.doors}, position={self.position}, rank={self.rank}, trunks={self.trunks}, dig_spots={self.dig_spots}, rarity={self.rarity}, has_been_entered={self.has_been_entered}, terminal={self.terminal})"

class ShopRoom(Room):
    def __init__(self, name="", cost=0, room_type="", description="", additional_info="", shape="", doors=None, position=None, rank=0, items_for_sale=None, trunks=0, dig_spots=0, rarity="", has_been_entered=False, terminal: Optional[Union[Terminal, SecurityTerminal, LabTerminal, OfficeTerminal, ShelterTerminal]] = None):
        super().__init__(name, cost, room_type, description, additional_info, shape, doors, position, rank, trunks, dig_spots, rarity, has_been_entered, terminal)
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
            print("q. Quit editing items")

            choice = input("Select an option: ").strip().lower()
            if choice == "1":
                item = input("Enter item name: ").strip().upper()
                price = input("Enter item price: ").strip()
                try:
                    price = int(price)
                    self.items_for_sale[item] = price
                    print(f"\nAdded {item} for {price} coins.")
                    time.sleep(1)
                except ValueError:
                    print("\nInvalid price. Please enter a number.")
                    time.sleep(1)
            elif choice == "2":
                item = input("Enter item name to remove: ").strip().upper()
                if item in self.items_for_sale:
                    del self.items_for_sale[item]
                    print(f"\nRemoved {item}.")
                    time.sleep(1)
                else:
                    print("\nItem not found.")
                    time.sleep(1)
            elif choice == "3":
                item = input("Enter item name to change price: ").strip().upper()
                if item in self.items_for_sale:
                    price = input("Enter new price: ").strip()
                    try:
                        price = int(price)
                        self.items_for_sale[item] = price
                        print(f"\nUpdated {item} price to {price} coins.")
                        time.sleep(1)
                    except ValueError:
                        print("\nInvalid price. Please enter a number.")
                        time.sleep(1)
                else:
                    print("\nItem not found.")
                    time.sleep(1)
            elif choice == "q":
                print("\nExiting item editor.")
                break
            else:
                print("\nInvalid option.")
                time.sleep(1)

    def to_dict(self):
        data = super().to_dict()
        data["items_for_sale"] = self.items_for_sale
        return data
    
    @classmethod
    def from_dict(cls, data):
        room = super().from_dict(data)
        room.items_for_sale = data.get("items_for_sale", {})
        return room
    
    def __str__(self):
        return super().__str__() + f", items_for_sale={self.items_for_sale})"

class PuzzleRoom(Room):
    def __init__(self, name="", cost=0, room_type="", description="", additional_info="", shape="", doors=None, position=None, rank=0, trunks=0, dig_spots=0, rarity="", has_been_entered=False, has_been_solved=False, terminal: Optional[Union[Terminal, SecurityTerminal, LabTerminal, OfficeTerminal, ShelterTerminal]] = None):
        super().__init__(name, cost, room_type, description, additional_info, shape, doors, position, rank, trunks, dig_spots, rarity, has_been_entered, terminal)
        self.has_been_solved = has_been_solved  # Indicates if the puzzle in this room has been solved

    def parlor_puzzle(self, reader: easyocr.Reader):
        """
        Interactive parlor puzzle solver.
        Prompts the user to screenshot each box and confirm correctness.
        """
        colors = ["BLUE", "WHITE", "BLACK"]
        results = {}
        for color in colors:
            input(f"Please get into position to screenshot the {color} box, press Enter to continue...")
            # Capture the hint using your existing OCR/parlor logic
            box_result = parlor.capture_hint(reader)
            print(f"OCR result for {color} box: {box_result}")
            confirm = input(f"Is the {color} box result correct? (y/n): ").strip().lower()
            if confirm == "y":
                results[color] = box_result
            else:
                print(f"Please retry the {color} box.")
                # Optionally, you could loop until confirmed
                while True:
                    input(f"Prepare to screenshot the {color} box again, press Enter to do so...")
                    box_result = parlor.capture_hint(reader)
                    print(f"OCR result for {color} box: {box_result}")
                    confirm = input(f"Is the {color} box result correct? (y/n): ").strip().lower()
                    if confirm == "y":
                        results[color] = box_result
                        break
        print("Parlor puzzle results:", results)
        return results
    
    def to_dict(self):
        data = super().to_dict()
        data["has_been_solved"] = self.has_been_solved
        return data
    
    @classmethod
    def from_dict(cls, data):
        room = super().from_dict(data)
        room.has_been_solved = data.get("has_been_solved", False)
        return room
    
    def __str__(self):
        return super().__str__() + f", has_been_solved={self.has_been_solved})"

class UtilityCloset(Room):
    """
        A utility closet containing various switches for different areas.

            Args: True means on, False means off
    """
    def __init__(self, name="", cost=0, room_type="", description="", additional_info="", shape="", doors=None, position=None, rank=0, trunks=0, dig_spots=0, rarity="", has_been_entered=False, terminal: Optional[Union[Terminal, SecurityTerminal, LabTerminal, OfficeTerminal, ShelterTerminal]] = None, keycard_entry_system_switch=True, gymnasium_switch=True, darkroom_switch=False, garage_switch=False):
        super().__init__(name, cost, room_type, description, additional_info, shape, doors, position, rank, trunks, dig_spots, rarity, has_been_entered, terminal)
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
        room = super().from_dict(data)
        room.keycard_entry_system_switch = data.get("keycard_entry_system_switch", True)
        room.gymnasium_switch = data.get("gymnasium_switch", True)
        room.darkroom_switch = data.get("darkroom_switch", False)
        room.garage_switch = data.get("garage_switch", False)
        return room
    
    def __str__(self):
        return super().__str__() + f", keycard_entry_system_switch={self.keycard_entry_system_switch}, gymnasium_switch={self.gymnasium_switch}, darkroom_switch={self.darkroom_switch}, garage_switch={self.garage_switch})"
    
class CoatCheck(Room):
    """
        Allows the player to store and retrieve an item across runs
    """
    def __init__(self, name="", cost=0, room_type="", description="", additional_info="", shape="", doors=None, position=None, rank=0, trunks=0, dig_spots=0, rarity="", has_been_entered=False, terminal: Optional[Union[Terminal, SecurityTerminal, LabTerminal, OfficeTerminal, ShelterTerminal]] = None, stored_item: Optional[str] = None):
        super().__init__(name, cost, room_type, description, additional_info, shape, doors, position, rank, trunks, dig_spots, rarity, has_been_entered, terminal)
        self.stored_item = stored_item

    def store_item(self, item: str):
        self.stored_item = item

    def retrieve_item(self) -> Optional[str]:
        self.stored_item = None
        return self.stored_item
    
    def to_dict(self):
        data = super().to_dict()
        data["stored_item"] = self.stored_item
        return data

    @classmethod
    def from_dict(cls, data):
        room = super().from_dict(data)
        room.stored_item = data.get("stored_item")
        return room

    def __str__(self):
        return super().__str__() + f", stored_item={self.stored_item})"