import time
from typing import Union
from capture.constants import DIRECTORY
from room import CoatCheck, PuzzleRoom, Room, ShopRoom, UtilityCloset
from terminal import LabTerminal, OfficeTerminal, SecurityTerminal, ShelterTerminal


class HouseMap:
    def __init__(self, width=5, height=9):
        self.width = width
        self.height = height
        self.grid = [[None for _ in range(width)] for _ in range(height)]

    def add_room_to_house(self, room: Room):
        x = room.position[0]
        y = room.position[1]
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError("Room position out of bounds.")
        self.grid[y][x] = room

    def get_room_by_position(self, x, y) -> Room:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return None
        return self.grid[y][x]
    
    def get_room_by_name(self, name: str) -> Union[Room, ShopRoom, PuzzleRoom, UtilityCloset, CoatCheck, None]:
        for row in self.grid:
            for room in row:
                if room and room.name == name:
                    return room
        return None
    
    def get_rooms_by_name(self, name: str) -> list[Room]:
        rooms = []
        for row in self.grid:
            for room in row:
                if room and room.name == name:
                    rooms.append(room)
        return rooms

    def prompt_for_room_name(self, initial_name: str = "") -> Room:
        name = initial_name
        while True:
            room = self.get_room_by_name(name)
            if room:
                return room
            name = input(f"\nDetected room '{name}' - but not found. Please enter a valid room name: ").strip().upper()

    def get_position_by_room(self, room: Room) -> tuple:
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == room:
                    return (x, y)
        return None
    
    def count_occupied_rooms(self) -> int:
        return sum(1 for row in self.grid for room in row if room)
    
    def scan_rooms_for_available_actions(self) -> dict:
        """
            scans all rooms in the house and sets flags if a room is a ShopRoom, PuzzleRoom,
            has a trunk, dig spot, terminal, or is a CoatCheck

                Returns:
                    None
        """
        flag_dict = {
            "shop_room_present": False,
            "puzzle_room_present": False,
            "trunk_present": False,
            "dig_spot_present": False,
            "terminal_present": False,
            "coat_check_present": False,
            "utility_closet_present": False
        }

        # exit early if all flags are True
        for row in self.grid:
            for room in row:
                if not room:
                    continue

                # check for ShopRoom
                if not flag_dict["shop_room_present"] and isinstance(room, ShopRoom):
                    flag_dict["shop_room_present"] = True
                # check for PuzzleRoom
                elif not flag_dict["puzzle_room_present"] and isinstance(room, PuzzleRoom):
                    flag_dict["puzzle_room_present"] = True
                # check for CoatCheck
                elif not flag_dict["coat_check_present"] and isinstance(room, CoatCheck):
                    flag_dict["coat_check_present"] = True
                # check for UtilityCloset
                elif not flag_dict["utility_closet_present"] and isinstance(room, UtilityCloset):
                    flag_dict["utility_closet_present"] = True
                # check for trunks
                if not flag_dict["trunk_present"] and getattr(room, "trunks", 0) > 0:
                    flag_dict["trunk_present"] = True
                # check for dig spots
                if not flag_dict["dig_spot_present"] and getattr(room, "dig_spots", 0) > 0:
                    flag_dict["dig_spot_present"] = True
                # check for terminal
                if not flag_dict["terminal_present"] and getattr(room, "terminal", None) is not None:
                    flag_dict["terminal_present"] = True

                # if all flags are True, exit early
                if (flag_dict["shop_room_present"] and flag_dict["puzzle_room_present"] and flag_dict["trunk_present"] and
                    flag_dict["dig_spot_present"] and flag_dict["terminal_present"] and flag_dict["coat_check_present"] and
                    flag_dict["utility_closet_present"]):
                    return flag_dict
        return flag_dict

    @staticmethod
    def specialize_room(room: Room) -> Union[ShopRoom, PuzzleRoom, UtilityCloset, CoatCheck]:
        if room.name in ["KITCHEN", "COMMISSARY", "LOCKSMITH", "SHOWROOM"]:
            return ShopRoom(**room.to_dict())
        elif room.name == "PARLOR":
            return PuzzleRoom(**room.to_dict())
        elif room.name == "UTILITY CLOSET":
            return UtilityCloset(**room.to_dict())
        elif room.name == "COAT CHECK":
            return CoatCheck(**room.to_dict())

    @staticmethod
    def autofill_room_attributes(room: Room, room_name: str) -> None:
        """
            Autofills room attributes from DIRECTORY using the provided room name

                Args:
                    room (Room): the room object to update
                    room_name (str): the name of the room to look up

                Returns:
                    None
        """
        if room_name == "SECURITY":
            room.terminal = SecurityTerminal()
        elif room_name == "OFFICE":
            room.terminal = OfficeTerminal()
        elif room_name == "LABORATORY":
            room.terminal = LabTerminal()
        elif room_name == "SHELTER":
            room.terminal = ShelterTerminal()
        for floor_type, rooms in DIRECTORY["FLOORPLANS"].items():
            if room_name in rooms:
                info = rooms[room_name]
                room.name = room_name
                room.shape = info.get("SHAPE", "")
                room.additional_info = info.get("ADDITIONAL_INFO", "")
                room.description = info.get("DESCRIPTION", "")
                room.rarity = info.get("RARITY", "")
                room.type = info.get("TYPE", [])
                room.cost = info.get("COST", 0)
                break
        else:
            print(f"Room '{room_name}' not found in DIRECTORY.")

    def edit_room(self, room: Union[Room, ShopRoom, PuzzleRoom, UtilityCloset]) -> None:
        """
            Allows the user to view and edit all editable fields of a Room or its subclasses

                Args:
                    room (Room): the room object to edit

                Returns:
                    None
        """
        # gather all editable fields, including subclass-specific ones
        editable_fields = [
            "name",
            "cost",
            "type",
            "description",
            "additional_info",
            "shape",
            "position",
            "doors",
            "rarity",
            "terminal",
            "trunks",
            "dig_spots",
            "has_been_entered"
        ]
        # add subclass-specific fields if present
        if hasattr(room, "items_for_sale"):
            editable_fields.append("items_for_sale")
        if hasattr(room, "has_been_solved"):
            editable_fields.append("has_been_solved")
        if hasattr(room, "keycard_entry_system_switch"):
            editable_fields.extend([
                "keycard_entry_system_switch",
                "gymnasium_switch",
                "darkroom_switch",
                "garage_switch"
            ])

        while True:
            print(f"\nEditing room at position: {getattr(room, 'position', None)}")
            print("Current values:")
            for field in editable_fields:
                print(f"  {field}: {getattr(room, field, None)}")
            print("\nType the attribute name to edit, or 'q' to quit editing.")

            field = input("Attribute to edit: ").strip()
            if field.lower() == "q":
                print("Exiting room attribute editor.")
                break
            if field not in editable_fields:
                print("Invalid attribute name.")
                continue
            current_value = getattr(room, field, None)
            # handle special fields
            if field == "cost" or field == "trunks" or field == "dig_spots":
                new_value = input(f"Enter new value for {field} (current: {current_value}): ").strip()
                try:
                    new_value = int(new_value)
                except ValueError:
                    print("Invalid input. Please enter a number.")
                    continue
            elif field == "position":
                new_value = input(f"Enter new value for position as x,y (current: {current_value}): ").strip()
                try:
                    x, y = map(int, new_value.strip("()").strip(" ").split(","))
                    new_value = (x, y)
                except Exception:
                    print("Invalid position format. Use x,y.")
                    continue
            elif field == "doors":
                print("Launching door editor...")
                room.edit_doors()
                continue
            elif field == "items_for_sale" and hasattr(room, "edit_items_for_sale"):
                print("Launching items for sale editor...")
                room.edit_items_for_sale()
                continue
            elif field == "has_been_entered" or field == "has_been_solved":
                new_value = input(f"Enter new value for {field} (True/False, current: {current_value}): ").strip().lower()
                new_value = new_value in ["true", "1", "yes", "y"]
            elif field in ["keycard_entry_system_switch", "gymnasium_switch", "darkroom_switch", "garage_switch"]:
                new_value = input(f"Enter new value for {field} (True/False, current: {current_value}): ").strip().lower()
                new_value = new_value in ["true", "1", "yes", "y"]
            else:
                new_value = input(f"Enter new value for {field} (current: {current_value}): ").strip()
            setattr(room, field, new_value)
            print(f"{field} updated.")

    def connect_adjacent_doors(self, new_room: Room):
        direction_opposite = {"N": "S", "S": "N", "E": "W", "W": "E"}
        x, y = new_room.position

        # First, connect new_room's doors as before
        for door in new_room.doors:
            dx, dy = 0, 0
            if door.orientation == "N":
                dy = -1
            elif door.orientation == "S":
                dy = 1
            elif door.orientation == "E":
                dx = 1
            elif door.orientation == "W":
                dx = -1
            neighbor_x, neighbor_y = x + dx, y + dy

            #if the neighbor would be out of bounds, the door leads to a dead end
            if not (0 <= neighbor_x < self.width and 0 <= neighbor_y < self.height):
                door.leads_to = "DEAD END"
                continue

            neighbor = self.get_room_by_position(neighbor_x, neighbor_y)
            if neighbor:
                matching_neighbor_door = None
                for neighbor_door in neighbor.doors:
                    if neighbor_door.orientation == direction_opposite[door.orientation]:
                        matching_neighbor_door = neighbor_door
                        break
                if matching_neighbor_door:
                    door.leads_to = neighbor.name
                    door.locked = False
                    matching_neighbor_door.leads_to = new_room.name
                    matching_neighbor_door.locked = False
                else:
                    door.leads_to = "DEAD END"

        # now, for all neighbors, check if any of their doors are blocked by the new room
        for dir, opp_dir in direction_opposite.items():
            dx, dy = 0, 0
            if dir == "N":
                dy = -1
            elif dir == "S":
                dy = 1
            elif dir == "E":
                dx = 1
            elif dir == "W":
                dx = -1
            neighbor_x, neighbor_y = x + dx, y + dy
            neighbor = self.get_room_by_position(neighbor_x, neighbor_y)
            if neighbor:
                for neighbor_door in neighbor.doors:
                    if neighbor_door.orientation == opp_dir:
                        # If new_room does NOT have a door facing neighbor, mark as DEAD END
                        if not any(d.orientation == dir for d in new_room.doors):
                            neighbor_door.leads_to = "DEAD END"   

    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "rooms": [
                [room.to_dict() if room else None for room in row]
                for row in self.grid
            ]
        }

    @staticmethod
    def from_dict(data):
        hm = HouseMap(width=data.get("width", 5), height=data.get("height", 9))
        hm.grid = [
            [Room.from_dict(room) if room else None for room in row]
            for row in data["rooms"]
        ]
        return hm

    #TODO: look at this a bit more
    @staticmethod
    def has_door(room, orientation):
        return any(door.orientation == orientation for door in room.doors)

    def print_map(self):
        print("\nCurrent House Map:\n")
        for y in range(self.height):
            row_str = ""
            connector_str = ""

            for x in range(self.width):
                room = self.grid[y][x]
                if room:
                    row_str += f"[{room.name[0]}]"
                else:
                    row_str += "[ ]"

                # Horizontal connector to room on the right
                if x < self.width - 1:
                    right_room = self.grid[y][x + 1]
                    if (
                        room and right_room and
                        self.has_door(room, "E") and self.has_door(right_room, "W")
                    ):
                        row_str += "─"
                    else:
                        row_str += " "

            print(row_str)

            # Now print vertical connections if not last row
            if y < self.height - 1:
                for x in range(self.width):
                    current = self.grid[y][x]
                    below = self.grid[y + 1][x]
                    if (
                        current and below and
                        self.has_door(current, "S") and self.has_door(below, "N")
                    ):
                        connector_str += " │ "
                    else:
                        connector_str += "   "
                    if x < self.width - 1:
                        connector_str += " "
                print(connector_str)

    def __repr__(self):
        return f"<HouseMap {self.width}x{self.height}>"