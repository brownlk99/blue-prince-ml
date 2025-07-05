from typing import Union, cast

from game.constants import DIRECTORY
from game.door import Door
from game.room import (CoatCheck,
    Laboratory,
    Office,
    PuzzleRoom,
    Room,
    SecretPassage,
    Security,
    Shelter,
    ShopRoom,
    UtilityCloset,
)
from utils import get_color_code


class HouseMap:
    """
        Represents a house map with rooms arranged in a grid layout

            Attributes:
                width: The width of the house map grid
                height: The height of the house map grid
                grid: A 2D list containing room objects or None for empty spaces
    """
    def __init__(self, width: int = 5, height: int = 9) -> None:
        """
            Initialize a HouseMap instance

                Args:
                    width: The width of the house map grid
                    height: The height of the house map grid
        """
        self.width = width
        self.height = height
        self.grid = [[None for _ in range(width)] for _ in range(height)]

    def add_room_to_house(self, room: Room) -> None:
        """
            Add a room to the house map at the room's position

                Args:
                    room: The room object to add to the house map
        """
        x = room.position[0]
        y = room.position[1]
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError("Room position out of bounds.")
        self.grid[y][x] = room

    def update_room_in_house(self, room: Room) -> None:
        """
            Update the room in the house map at its current position by removing and adding

                Args:
                    room: The room object to update in the house map
        """
        x, y = room.position
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError("Room position out of bounds.")
        existing_room = self.grid[y][x]
        if existing_room is None:
            raise ValueError("No room exists at the specified position to update.")
        self.grid[y][x] = room

    def get_room_by_position(self, x: int, y: int) -> Union[Room, ShopRoom, PuzzleRoom, UtilityCloset, CoatCheck, SecretPassage, None]:
        """
            Get a room from the house map by its position coordinates

                Args:
                    x: The x coordinate of the room
                    y: The y coordinate of the room

                Returns:
                    The room object at the specified position or None if no room exists
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            return None
        return self.grid[y][x]
    
    def get_room_by_name(self, name: str) -> Union[Room, ShopRoom, PuzzleRoom, UtilityCloset, CoatCheck, SecretPassage, None]:
        """
            Get the first room from the house map by its name

                Args:
                    name: The name of the room to find

                Returns:
                    The first room object with the specified name or None if not found
        """
        for row in self.grid:
            for room in row:
                if room and room.name == name:
                    return room
        return None
    
    def get_rooms_by_name(self, name: str) -> list[Room]:
        """
            Get all rooms from the house map by their name

                Args:
                    name: The name of the rooms to find

                Returns:
                    A list of room objects with the specified name
        """
        rooms = []
        for row in self.grid:
            for room in row:
                if room and room.name == name:
                    rooms.append(room)
        return rooms

    def prompt_for_room_name(self, initial_name: str = "") -> Room:
        """
            Prompt the user to enter a valid room name and return the room

                Args:
                    initial_name: The initial room name to check

                Returns:
                    The room object with the valid name
        """
        name = initial_name
        while True:
            room = self.get_room_by_name(name)
            if room:
                return room
            name = input(f"Detected room '{name}' - but not found within the house. Please enter a valid room name: ").strip().upper()
    
    def count_occupied_rooms(self) -> int:
        """
            Count the number of occupied rooms in the house map

                Returns:
                    The number of rooms that are not None
        """
        return sum(1 for row in self.grid for room in row if room)
    
    def scan_rooms_for_available_actions(self) -> dict:
        """
            Scan all rooms in the house and set flags if a room is a ShopRoom, PuzzleRoom, has a trunk, dig spot, terminal, or is a CoatCheck

                Returns:
                    A dictionary containing boolean flags for different room types and features
        """
        flag_dict = {
            "shop_room_present": False,
            "puzzle_room_present": False,
            "trunk_present": False,
            "dig_spot_present": False,
            "terminal_present": False,
            "coat_check_present": False,
            "utility_closet_present": False,
            "secret_passage_present": False
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
                elif not flag_dict["puzzle_room_present"] and isinstance(room, PuzzleRoom) and not room.has_been_solved:
                    flag_dict["puzzle_room_present"] = True
                # check for CoatCheck
                elif not flag_dict["coat_check_present"] and isinstance(room, CoatCheck):
                    flag_dict["coat_check_present"] = True
                # check for UtilityCloset
                elif not flag_dict["utility_closet_present"] and isinstance(room, UtilityCloset):
                    flag_dict["utility_closet_present"] = True
                elif not flag_dict["secret_passage_present"] and room.name == "SECRET PASSAGE" and not room.has_been_used:
                    flag_dict["secret_passage_present"] = True
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
    def specialize_room(room: Room) -> Union[Room, ShopRoom, PuzzleRoom, UtilityCloset, CoatCheck, SecretPassage, Security, Office, Laboratory, Shelter]:
        """
            Specialize a room type based on its name

                Args:
                    room: The room object to specialize

                Returns:
                    The specialized room type
        """
        if room.name in ["KITCHEN", "COMMISSARY", "LOCKSMITH", "SHOWROOM"]:
            return ShopRoom.from_dict(room.to_dict())
        elif room.name == "PARLOR":
            return PuzzleRoom.from_dict(room.to_dict())
        elif room.name == "UTILITY CLOSET":
            return UtilityCloset.from_dict(room.to_dict())
        elif room.name == "COAT CHECK":
            return CoatCheck.from_dict(room.to_dict())
        elif room.name == "SECRET PASSAGE":
            return SecretPassage.from_dict(room.to_dict())
        elif room.name == "SECURITY":       # the following rooms rely on the terminal being present (which it never will be as Room doesnt have that attribute so it must be created)
            return Security.from_dict(room.to_dict())
        elif room.name == "OFFICE":
            return Office.from_dict(room.to_dict())
        elif room.name == "LABORATORY":
            return Laboratory.from_dict(room.to_dict())
        elif room.name == "SHELTER":
            return Shelter.from_dict(room.to_dict())
        else:
            # If the room is not a special type, return it as is
            return room

    @staticmethod
    def generic_autofill_room_attributes(room: Room, room_name: str) -> None:
        """
            Autofill room attributes from DIRECTORY using the provided room name

                Args:
                    room: The room object to update
                    room_name: The name of the room to look up
        """
        for _, rooms in DIRECTORY["FLOORPLANS"].items():
            if room_name in rooms:
                info = rooms[room_name]
                room.name = room_name
                room.shape = info.get("SHAPE", "")
                room.additional_info = info.get("ADDITIONAL_INFO", "")
                room.description = info.get("DESCRIPTION", "")
                room.rarity = info.get("RARITY", "")
                room.type = info.get("TYPE", [])
                room.cost = info.get("COST", 0)
                room.add_door_interactive(info.get("NUM_DOORS", 0))
                break
        else:
            print(f"Room '{room_name}' not found in DIRECTORY.")

    def edit_room(self, room: Union[Room, ShopRoom, PuzzleRoom, UtilityCloset]) -> None:
        """
            Allow the user to view and edit all editable fields of a Room or its subclasses

                Args:
                    room: The room object to edit
        """
        # gather all editable fields, including subclass-specific ones
        #TODO: maybe add type back in
        editable_fields = [
            "name",
            "cost",
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
            elif field == "items_for_sale" and hasattr(room, "edit_items_for_sale") and isinstance(room, ShopRoom):
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

    def connect_adjacent_doors(self, new_room: Room) -> None:
        """
            Connect adjacent doors between the new room and existing neighboring rooms

                Args:
                    new_room: The new room to connect to its neighbors
        """
        direction_opposite = {"N": "S", "S": "N", "E": "W", "W": "E"}
        x, y = new_room.position

        # first, connect new_room's doors as before
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

            # if the neighbor would be out of bounds, the door leads to a dead end
            if not (0 <= neighbor_x < self.width and 0 <= neighbor_y < self.height):
                door.leads_to = "BLOCKED"
                door.locked = "N/A"
                door.is_security = "N/A"
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
                    door.locked = str(False)
                    door.is_security = matching_neighbor_door.is_security
                    matching_neighbor_door.leads_to = new_room.name
                    matching_neighbor_door.locked = str(False)
                else:
                    door.leads_to = "BLOCKED"
                    door.locked = "N/A"
                    door.is_security = "N/A"

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
                        # if new_room does NOT have a door facing neighbor, mark as DEAD END
                        if not any(d.orientation == dir for d in new_room.doors):
                            neighbor_door.leads_to = "BLOCKED"
                            neighbor_door.locked = "N/A"
                            neighbor_door.is_security = "N/A"


    def update_security_doors(self) -> None:
        """
            Update all security doors based on current Security room terminal settings and the Utility Closet keycard_entry_system_switch status
        """
        # find the Security room and Utility Closet
        security_room = self.get_room_by_name("SECURITY")
        utility_closet = self.get_room_by_name("UTILITY CLOSET")
        
        # default to security doors being locked unless specific conditions are met
        unlock_all_security = False
        
        # check if conditions are met to globally unlock security doors
        # this requires both rooms to be present and of the correct type
        if isinstance(security_room, Security) and isinstance(utility_closet, UtilityCloset):
            if (security_room.terminal.offline_mode == "UNLOCKED" and not utility_closet.keycard_entry_system_switch):
                unlock_all_security = True

        # update all security doors in the house
        for row in self.grid:
            for room in row:
                if room:
                    for door in cast(list[Door], room.doors):
                        # we only care about doors that are marked as security doors
                        if str(getattr(door, 'is_security', 'false')).lower() != "true":
                            continue

                        if unlock_all_security:
                            # if the master unlock is active, unlock all security doors
                            door.locked = str(False)
                        elif door.leads_to == "?":
                            # if the master unlock is NOT active, only lock security doors
                            # that haven't been opened yet
                            door.locked = str(True)

    def to_dict(self) -> dict:
        """
            Convert the HouseMap instance to a dictionary representation

                Returns:
                    A dictionary representation of the house map
        """
        return {
            "width": self.width,
            "height": self.height,
            "rooms": [
                [room.to_dict() if room else None for room in row]
                for row in self.grid
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'HouseMap':
        """
            Create a HouseMap instance from a dictionary representation

                Args:
                    data: A dictionary containing house map data

                Returns:
                    A HouseMap instance created from the dictionary data
        """
        hm = HouseMap(width=data.get("width", 5), height=data.get("height", 9))
        hm.grid = []
        for row in data["rooms"]:
            grid_row = []
            for room_data in row:
                if room_data is None:
                    grid_row.append(None)
                else:
                    # determine the correct room type and call appropriate from_dict
                    room_name = room_data.get("name", "")
                    if room_name in ["KITCHEN", "COMMISSARY", "LOCKSMITH", "SHOWROOM"]:
                        grid_row.append(ShopRoom.from_dict(room_data))
                    elif room_name == "PARLOR":
                        grid_row.append(PuzzleRoom.from_dict(room_data))
                    elif room_name == "UTILITY CLOSET":
                        grid_row.append(UtilityCloset.from_dict(room_data))
                    elif room_name == "COAT CHECK":
                        grid_row.append(CoatCheck.from_dict(room_data))
                    elif room_name == "SECRET PASSAGE":
                        grid_row.append(SecretPassage.from_dict(room_data))
                    elif room_name == "SECURITY":
                        grid_row.append(Security.from_dict(room_data))
                    elif room_name == "OFFICE":
                        grid_row.append(Office.from_dict(room_data))
                    elif room_name == "LABORATORY":
                        grid_row.append(Laboratory.from_dict(room_data))
                    elif room_name == "SHELTER":
                        grid_row.append(Shelter.from_dict(room_data))
                    else:
                        grid_row.append(Room.from_dict(room_data))
            hm.grid.append(grid_row)
        return hm

    def print_map(self) -> None:
        """
            Print an enhanced, informative house map with different symbols for door states
        """
        print("\n" + "="*60)
        print("CURRENT HOUSE MAP")
        print("="*60)
        
        # legend
        print("\nLEGEND:")
        print("   Rooms: [A] = First letter of room name (color-coded)")
        print("   Connections:")
        print("     - | = Open passage     ? = Unknown door")
        print("     X   = Blocked door     L = Locked door")
        print("     S   = Security door    = | = Unlocked passage")
        print("     *   = Special door")
        print("-"*60)
        
        for y in range(self.height):
            row_str = ""
            connector_str = ""

            for x in range(self.width):
                room = self.grid[y][x]
                if room:
                    # get room abbreviation (first letter only)
                    abbrev = self._get_room_abbreviation(room.name)
                    room_display = f"{abbrev}  "
                    row_str += f"[{room_display}]"
                else:
                    row_str += "[   ]"

                # horizontal connector to room on the right
                if x < self.width - 1:
                    right_room = self.grid[y][x + 1]
                    connector = self._get_horizontal_connector(room, right_room)
                    row_str += connector

            print(row_str)

            # vertical connections if not last row
            if y < self.height - 1:
                for x in range(self.width):
                    current = self.grid[y][x]
                    below = self.grid[y + 1][x]
                    connector = self._get_vertical_connector(current, below)
                    connector_str += connector
                    
                    if x < self.width - 1:
                        connector_str += "  "  # space between vertical connectors
                        
                if connector_str.strip():  # only print if there are actual connectors
                    print(connector_str)
                connector_str = ""

        print("="*60)
        print("TIP: Use 'edit_doors' to modify door properties")
        print("="*60)

    def _get_room_abbreviation(self, room_name: str) -> str:
        """
            Get the first letter of room name with color coding

                Args:
                    room_name: The name of the room

                Returns:
                    The first letter of the room name with color coding applied
        """
        if not room_name:
            return " "
        
        # get the color-coded full name
        colored_name = get_color_code(room_name)
        
        # if it's the same as the input (no color applied), just return first letter
        if colored_name == room_name.upper():
            return room_name[0]
        
        # extract the color code and apply it to just the first letter
        # the format is: \033[XXm + NAME + \033[0m
        # we want: \033[XXm + FIRST_LETTER + \033[0m
        if '\033[' in colored_name:
            # find the first reset code
            reset_pos = colored_name.find('\033[0m')
            if reset_pos != -1:
                # extract color code (everything before the room name)
                color_start = colored_name.find('\033[')
                color_end = colored_name.find('m', color_start) + 1
                color_code = colored_name[color_start:color_end]
                return f"{color_code}{room_name[0]}\033[0m"
        
        return room_name[0]

    def _get_horizontal_connector(self, left_room: Union[Room, None], right_room: Union[Room, None]) -> str:
        """
            Get the appropriate horizontal connector symbol between two rooms

                Args:
                    left_room: The room on the left side
                    right_room: The room on the right side

                Returns:
                    The appropriate connector symbol string
        """
        if not left_room or not right_room:
            return "  "
        
        # check if rooms have connecting doors
        left_door = self._get_door_by_orientation(left_room, "E")
        right_door = self._get_door_by_orientation(right_room, "W")
        
        if not left_door or not right_door:
            return "  "
        
        # determine connector type based on door states
        connector = self._get_door_connector_symbol(left_door, right_door, horizontal=True)
        return f"{connector} "

    def _get_vertical_connector(self, top_room: Union[Room, None], bottom_room: Union[Room, None]) -> str:
        """
            Get the appropriate vertical connector symbol between two rooms

                Args:
                    top_room: The room on the top
                    bottom_room: The room on the bottom

                Returns:
                    The appropriate connector symbol string
        """
        if not top_room or not bottom_room:
            return "     "
        
        # check if rooms have connecting doors
        top_door = self._get_door_by_orientation(top_room, "S")
        bottom_door = self._get_door_by_orientation(bottom_room, "N")
        
        if not top_door or not bottom_door:
            return "     "
        
        # determine connector type based on door states
        connector = self._get_door_connector_symbol(top_door, bottom_door, horizontal=False)
        return f"  {connector}  "

    def _get_door_by_orientation(self, room: Union[Room, None], orientation: str) -> Union[Door, None]:
        """
            Get a door from a room by its orientation

                Args:
                    room: The room to search for doors
                    orientation: The orientation of the door to find

                Returns:
                    The door with the specified orientation or None if not found
        """
        if not room or not hasattr(room, 'doors'):
            return None
        return next((door for door in room.doors if door.orientation == orientation), None)

    def _get_door_connector_symbol(self, door1: Union[Door, None], door2: Union[Door, None], horizontal: bool = True) -> str:
        """
            Get the appropriate connector symbol based on door states

                Args:
                    door1: The first door
                    door2: The second door
                    horizontal: Whether the connection is horizontal

                Returns:
                    The appropriate connector symbol
        """
        if not door1 or not door2:
            return "X"
        
        # check for blocked connections
        if (hasattr(door1, 'leads_to') and door1.leads_to == "BLOCKED") or \
           (hasattr(door2, 'leads_to') and door2.leads_to == "BLOCKED"):
            return "X"
        
        # check for unknown/unexplored doors
        if (hasattr(door1, 'leads_to') and door1.leads_to == "?") or \
           (hasattr(door2, 'leads_to') and door2.leads_to == "?"):
            return "?"
        
        # check for security doors
        if (hasattr(door1, 'is_security') and str(door1.is_security).lower() == "true") or \
           (hasattr(door2, 'is_security') and str(door2.is_security).lower() == "true"):
            return "S"
        
        # check for locked doors
        if (hasattr(door1, 'locked') and str(door1.locked).lower() == "true") or \
           (hasattr(door2, 'locked') and str(door2.locked).lower() == "true"):
            return "L"
        
        # check for special unlocked passages (both doors explicitly unlocked)
        if (hasattr(door1, 'locked') and str(door1.locked).lower() == "false") and \
           (hasattr(door2, 'locked') and str(door2.locked).lower() == "false"):
            return "=" if horizontal else "|"
        
        # default open passage
        return "-" if horizontal else "|"

    def __repr__(self) -> str:
        """
            Return a string representation of the HouseMap

                Returns:
                    A string representation showing the dimensions of the house map
        """
        return f"<HouseMap {self.width}x{self.height}>"