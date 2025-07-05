import json
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from game.constants import DIRECTORY
from game.note import Note
from game.room import Room


class BaseMemory(ABC):
    """
        Base class for all memory types with common JSON persistence functionality

            Attributes:
                path: The file path for storing the memory data
                data: The actual memory data stored in this instance
    """
    
    def __init__(self, path: str, default_data: Any = None) -> None:
        """
            Initialize a BaseMemory instance

                Args:
                    path: The file path for storing the memory data
                    default_data: Default data to use if no file exists
        """
        self.path = path
        self.data = self._load_data(default_data)
    
    def _load_data(self, default_data: Any) -> Any:
        """
            Load data from JSON file or return default

                Args:
                    default_data: Default data to return if file doesn't exist

                Returns:
                    The loaded data from file or default data
        """
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return default_data if default_data is not None else self._get_default_data()
    
    @abstractmethod
    def _get_default_data(self) -> Any:
        """
            Return the default data structure for this memory type

                Returns:
                    The default data structure for this memory type
        """
        pass
    
    def save(self) -> None:
        """
            Save data to JSON file
        """
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def reset(self) -> None:
        """
            Reset to default data and save
        """
        self.data = self._get_default_data()
        self.save()


class NoteMemory(BaseMemory):
    """
        Memory class for storing game notes with intro note initialization

            Attributes:
                path: The file path for storing note data
                data: List of note dictionaries
    """
    def __init__(self, path: str = "./jsons/notes.json") -> None:
        """
            Initialize a NoteMemory instance

                Args:
                    path: The file path for storing note data
        """
        super().__init__(path)
        self._ensure_intro_note()
    
    def _get_default_data(self) -> List[Dict[str, Any]]:
        """
            Return default empty list for note data

                Returns:
                    An empty list for storing notes
        """
        return []
    
    def _ensure_intro_note(self) -> None:
        """
            Ensure the intro note exists in the notes
        """
        intro_note = Note(
            title="Intro Monologue",
            content="I, Herbert S. Sinclair, of the Mount Holly Estate at Reddington,\n"
                "do publish, and declare, this instrument,\n"
                "my last will and testament,\n"
                "and hereby revoke all wills and codicils heretofore made by me.\n"
                "I give and bequeath to my grandnephew, Simon P. Jones,\n"
                "son of my dear niece, Mary Matthew,\n"
                "all of my right, title and interest in\n"
                "and to the house and land which I own near Mount Holly\n"
                "The above provision and bequest is contingent on my aforementioned grand-nephew discovering\n"
                "the location of the 46th room of my forty-five room estate.\n"
                "The location of the room has been kept a secret from all the staff and servants of the manor,\n"
                "but I am confident that any heir worthy of the Sinclair legacy should have no trouble uncovering its whereabouts\n"
                "within a timely manner.\n"
                "Should my grandnephew fail to uncover this room or provide proof of his discovery\n"
                "to the executors of my will then this gift shall lapse.\n"
                "In witness whereof, I have hereunto set my hand this 18th day of March, 1993.\n\n"
                "Herbert S. Sinclair",
            found_in_room="N/A",
            color="N/A"
        )
        self.add_to_json(intro_note)
        
    def add_to_json(self, note: Note) -> None:
        """
            Add a note to the memory if it doesn't already exist

                Args:
                    note: The Note instance to add
        """
        existing_hashes = {n.get("hash") for n in self.data}
        if note.hash not in existing_hashes:
            self.data.append(note.to_dict())
            self.save()


class TermMemory(BaseMemory):
    """
        Memory class for storing game terminology and definitions

            Attributes:
                path: The file path for storing term data
                data: Dictionary of term definitions
    """
    def __init__(self, path: str = "./jsons/term_memory.json") -> None:
        """
            Initialize a TermMemory instance

                Args:
                    path: The file path for storing term data
        """
        super().__init__(path)

    def _get_default_data(self) -> Dict[str, str]:
        """
            Return default dictionary of game terms and definitions

                Returns:
                    A dictionary containing default game terms and their definitions
        """
        return {
            "ADJOINING": "Rooms are considered adjoined if they are connected to each other via a doorway.",
            "BEDROOM": "One of the most common type of rooms. BEDROOMS are typically used for resting and regaining steps, and are identifiable by the violet borders of their floorplans.",
            "CALL IT A DAY": "You may CALL IT A DAY at any time. This will end the current day and reset the rooms on the ESTATE, your inventory and your steps. When you run out of steps, you will be forced to CALL IT A DAY.",
            "COLOR": "The color of a floorplan will usually indicate the type of room: VIOLET for BEDROOMS, ORANGE for HALLWAYS, GREEN for GREEN ROOMS, YELLOW for SHOPS, RED for RED ROOMS, and BLUE for BLUEPRINTS (default type)",
            "DEAD END": "A DEAD END is any room lacking a second doorway. If a room ever has additional doorways it is not considered a dead end, even if those doorways are blocked.",
            "DRAFTING": "The action of selecting a floorplan from the three options presented to you after clicking a door is known as DRAFTING.",
            "DRAFTING (TYPE)": "Certain rooms can affect the drafting pool and the drafting process. This type of room is fittingly known as a \"DRAFTING ROOM\" are are noted on their floorplans by the compass symbol.",
            "DRAFT POOL": "The total collection of currently available floorplans, from which three are drawn at the beginning of each draft.",
            "DRAW": "Drawing is the initial pulling of the three floorplans from the draft pool at the beginning of drafting. To illustrate the difference between drawing and drafting, remember that \"Three floorplans are drawn, but only one is drafted.\"",
            "ESTATE": "Refers to all the explorable areas of Mt. Holly including the rooms currently drafted, as well as the GROUNDS. The HOUSE, on the other hand, is only referring to the current rooms, as shown on the Mt. Holly Blueprint.",
            "EXHAUST": "When your steps reach zero, you are exhausted and too tired to continue exploring. At this point, you must call it a day.",
            "FLOORPLAN": "The life of every room begins as a floorplan, a square paper sketch, drawn by an architect, from a pool of potential ideas - the draft pool.",
            "GEMS": "A valuable resources used to draft special FLOORPLANS (the \"COST\" of drafting a particular FLOORPLAN).",
            "GOLD (COINS)": "The currency by which you can purchase goods and services from the SHOP rooms on the ESTATE.",
            "GREEN ROOM": "FLOORPLANS that have a green border are known as GREEN ROOMS, These rooms are associated with outdoor areas and gardens, and are naturally synergistic with one another.",
            "HALLWAY": "Orange FLOORPLANS, known as HALLWAYS, are rooms that often contain many doors. They provide architects the means to branch off into different paths, allowing for greater flexibility.",
            "HOUSE": "The house refers to the 45-floorplan grid of Mount Holly. Only the rooms currently drafted are considered to be part of the HOUSE.",
            "INVENTORY": "The ITEMS you have collected on any given day",
            "ITEMS": "ITEMS refer both to SPECIAL ITEMS (unique items in your inventory), as well as RESOURCE ITEMS such as KEYS, GEMS, GOLD etc.",
            "KEYS": "KEYS are a common resource used to open up LOCKED doors on the ESTATE. There are also some unique SPECIAL KEYS that can unlock special doors or rooms that only appear in specific locations in the HOUSE.",
            "KEYCARD DOOR": "Electric powered doors of reinforced steel that can only be accessed via KEYCARD and are considered SECURITY LOCKED. These doors appear with more frequency the higher up in RANK you are in the HOUSE.",
            "LOCKED": "As you explore the house you will find that some doors are LOCKED. To continue exploring, you will need to use a KEY to unlock them.",
            "RANK": "Each row of rooms in your HOUSE make up a RANK. As you progress north, the RANK increases. There are nine ranks listed on Mount Holly's official blueprint. However, among the staff, whispers of a tenth Rank can often be heard.",
            "RARITY": "How often a FLOORPLAN is drawn from the drafting pool is determined by its RARITY. There are four rarities: COMMONPLACE, NORMAL, UNCOMMON, and RARE",
            "REDRAW": "Some rooms and ITEMS allow you to throw back the first three options drawn from the drafting pool for a fresh set of potential rooms. This is known as drawing new FLOORPLANS.",
            "RED ROOM": "Beware the rooms of red! They offer powerful expansion options but come at a dangerous cost.",
            "RESET": "Each morning, the house returns to its default position and all drafted rooms, inventory and resources are RESET. PERMANENT changes, however, do not RESET.",
            "SHOP": "FLOORPLANS adorned by borders of golden yellow are SHOPS that typically offer goods or a service in exchange for COINS.",
            "SPECIAL FLOORPLAN": "These FLOORPLANS are slightly more rare and cost GEMS to draft. They often offer more unique, complex and exciting effects.",
            "SPECIAL ITEM": "An item that is unique and inventory bound, as opposed to resource items such as KEYS, GEMS or COINS.",
            "SPREAD": "When a SPREAD occurs, ITEMS are randomly distributed across all rooms currently active on the ESTATE. The more rooms in your HOUSE, the larger the spread.",
            "TERMINAL": "Mt. Holly is equipped with several state of the art computer TERMINAL stations that control various systems on the ESTATE electronically. Each terminal is also connected to a central local NETWORK.",
            "TOMORROW": "Rooms that provide benefits in the future belong to a special category of floorplans: TOMORROW ROOMS. They are marked with a clock symbol.",
            "TRUNK": "A small wooden chest often found in rooms, always LOCKED, and usually containing a few items of interest.",
            "BLOCKED": "If a DOOR is marked as BLOCKED, it is not possible to enter it."
        }

    def automated_add_term(self, key: str, description: str) -> None:
        """
            Add a term to memory if it doesn't already exist

                Args:
                    key: The term key to add
                    description: The description of the term
        """
        if key.upper() not in self.data:
            self.data[key.upper()] = description
            self.save()

    def user_facilitated_add_term(self) -> None:
        """
            Interactive method to add terms from the directory to memory
        """
        # combine TERMS and ITEMS for selection
        all_terms = {**DIRECTORY.get("TERMS", {}), **DIRECTORY.get("ITEMS", {})}
        # only show terms/items not already in persistent memory
        available_terms = {k: v for k, v in all_terms.items() if k.upper() not in self.data}

        if not available_terms:
            print("All terms/items are already in persistent memory.")
            return

        while True:
            print("\nAvailable terms/items to add:")
            for idx, (term, desc) in enumerate(available_terms.items(), 1):
                print(f"{idx}. {term}: {desc}")
            print("\nType the key of the term/item to add, or 'q' to quit.")

            choice = input("Your choice: ").strip()
            if choice.lower() == 'q':
                print("Exiting add-to-memory.")
                break

            key = choice.upper()
            if key in available_terms:
                self.automated_add_term(key, available_terms[key])
                print(f"\nAdded '{key}' to persistent memory.")
                time.sleep(1)
                # remove from available_terms so it doesn't show again
                del available_terms[key]
                if not available_terms:
                    print("\nAll terms/items have been added.")
                    time.sleep(2)
                    break
            else:
                print("\nInvalid key. Please type the exact key from the list or 'q' to quit.")
                time.sleep(2)
        self.save()
        

    def get_term(self, key: str) -> Optional[str]:
        """
            Get a term definition by key

                Args:
                    key: The term key to look up

                Returns:
                    The term definition or None if not found
        """
        return self.data.get(key.upper())
    

class RoomMemory(BaseMemory):
    """
        Memory class for storing room information and characteristics

            Attributes:
                path: The file path for storing room data
                data: Dictionary of room data indexed by room name
    """
    def __init__(self, path: str = "./jsons/room_memory.json") -> None:
        """
            Initialize a RoomMemory instance

                Args:
                    path: The file path for storing room data
        """
        super().__init__(path)

    def _get_default_data(self) -> Dict[str, Any]:
        """
            Return default empty dictionary for room data

                Returns:
                    An empty dictionary for storing room data
        """
        return {}

    def add_room(self, room: Room) -> None:
        """
            Add a room to memory if it doesn't already exist

                Args:
                    room: The Room instance to add to memory
        """
        if room.name.upper() in self.data:
            print(f"{room.name} is already in memory. Skipping.")
            return
        room_data = room.to_dict()
        filtered_data = {
            "cost": room_data["cost"],
            "type": room_data["type"],
            "description": room_data["description"],
            "additional_info": room_data["additional_info"],
            "shape": room_data["shape"],
            "rarity": room_data["rarity"],
        }
        self.data[room.name.upper()] = filtered_data
        self.save()

    def get_room(self, room_name: str) -> Optional[Dict[str, Any]]:
        """
            Get room data by name

                Args:
                    room_name: The name of the room to look up

                Returns:
                    The room data dictionary or None if not found
        """
        return self.data.get(room_name.upper())


class PreviousRunMemory(BaseMemory):
    """
        Memory class for storing information about previous game runs

            Attributes:
                path: The file path for storing previous run data
                data: List of previous run dictionaries
    """
    def __init__(self, path: str = "./jsons/previous_run_memory.json") -> None:
        """
            Initialize a PreviousRunMemory instance

                Args:
                    path: The file path for storing previous run data
        """
        super().__init__(path)

    def _get_default_data(self) -> List[Dict[str, Any]]:
        """
            Return default empty list for previous run data

                Returns:
                    An empty list for storing previous run data
        """
        return []

    def add_run(self, day: int, reason: str, stored_item: str = "") -> None:
        """
            Add a run to the previous run memory

                Args:
                    day: The day of the run
                    reason: The reason for ending the run
                    stored_item: The item stored in coat check (optional)
        """
        self.data.append({
            "day": day,
            "reason": reason,
            "stored_item": stored_item
        })
        self.save()

    def get_most_recent_run(self) -> Dict[str, Any]:
        """
            Get the most recent run if it exists

                Returns:
                    The most recent run dictionary, or an empty dict if none exist
        """
        if self.data:
            return self.data[-1]
        return {}


class DecisionMemory(BaseMemory):
    """
        Memory class for storing game decision contexts

            Attributes:
                path: The file path for storing decision data
                data: List of decision dictionaries
    """
    def __init__(self, path: str = "./jsons/decision_memory.json") -> None:
        """
            Initialize a DecisionMemory instance

                Args:
                    path: The file path for storing decision data
        """
        super().__init__(path)

    def _get_default_data(self) -> List[Dict[str, Any]]:
        """
            Return default empty list for decision data

                Returns:
                    An empty list for storing decision data
        """
        return []

    def add_decision(self, decision: Dict[str, Any]) -> None:
        """
            Add a decision to the memory

                Args:
                    decision: The decision dictionary to add
        """
        self.data.append(decision)
        self.save()

    def get_move_context(self) -> Optional[Dict[str, Any]]:
        """
            Get the most recent move decision context if it exists

                Returns:
                    The most recent move decision context or None if not found
        """
        # search through decisions in reverse order (most recent first)
        for decision in reversed(self.data):
            if isinstance(decision, dict) and decision.get("action") == "move":
                return {
                    "target_room": decision.get("target_room", ""),
                    "planned_action": decision.get("planned_action", ""),
                    "explanation": decision.get("explanation", "")
                }
        return None


class BookMemory(BaseMemory):
    """
        Memory class for storing book information

            Attributes:
                path: The file path for storing book data
                data: List of book dictionaries
    """
    def __init__(self, path: str = "./jsons/book_memory.json") -> None:
        """
            Initialize a BookMemory instance

                Args:
                    path: The file path for storing book data
        """
        super().__init__(path)

    def _get_default_data(self) -> List[Dict[str, Any]]:
        """
            Return default empty list for book data

                Returns:
                    An empty list for storing book data
        """
        return []

    def add_book(self, book: Dict[str, Any]) -> None:
        """
            Add a book to the memory

                Args:
                    book: The book dictionary to add
        """
        self.data.append(book)
        self.save()