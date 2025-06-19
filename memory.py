import json
import os
import time
from typing import Any, Dict, List
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from note import Note

from capture.constants import DIRECTORY
from room import CoatCheck, Room

class NoteMemory:
    def __init__(self, persist_path="./note_db"):
        self.persist_path = persist_path
        self.json_path = "./jsons/notes.json"
        self.embedder = OpenAIEmbeddings(model="text-embedding-3-small")

        # Load existing DB or create new
        self.store = Chroma(
            embedding_function=self.embedder,
            persist_directory=self.persist_path
        )

        self.existing_hashes = {m.get("hash") for m in self.store.get()["metadatas"] if m}

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
        if intro_note.hash_note() not in self.existing_hashes:
            self.add_to_vector_db(intro_note)
            self.add_to_json(intro_note)
        
    def add_to_vector_db(self, note: Note):
        h = note.hash_note()
        if h in self.existing_hashes:
            print("Duplicate note, skipping.")
            return

        doc = Document(
            page_content=note.content,
            metadata={
                "title": note.title,
                "room": note.found_in_room,
                "color": note.color,
                "hash": h
            }
        )
        self.store.add_documents([doc])
        self.existing_hashes.add(h)

    def clear_vector_db(self):
        # Remove all documents from the Chroma store
        self.store.delete_collection()
        # Re-initialize the store to ensure it's empty and ready for new notes
        self.store = Chroma(
            embedding_function=self.embedder,
            persist_directory=self.persist_path
        )
        self.existing_hashes = set()

    def add_to_json(self, note: Note):
        if os.path.exists(self.json_path):
            with open(self.json_path, "r", encoding="utf-8") as f:
                notes = json.load(f)
        else:
            notes = []

        notes.append(note.to_dict())
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2, ensure_ascii=False)

    def search(self, query: str, k=3):
        return self.store.similarity_search(query, k=k)

class TermMemory:
    def __init__(self, path="./jsons/term_memory.json"):
        self.path = path
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.terms = json.load(f)
        else:
            self.terms = {}

    def automated_add_term(self, key, description):
        self.terms[key.upper()] = description
        self.save()

    def user_facilitated_add_term(self):
        # Combine TERMS and ITEMS for selection
        all_terms = {**DIRECTORY.get("TERMS", {}), **DIRECTORY.get("ITEMS", {})}
        # Only show terms/items not already in persistent memory
        available_terms = {k: v for k, v in all_terms.items() if k.upper() not in self.terms}

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
                # Remove from available_terms so it doesn't show again
                del available_terms[key]
                if not available_terms:
                    print("All terms/items have been added.")
                    break
            else:
                print("Invalid key. Please type the exact key from the list or 'q' to quit.")

    def reset(self):
        self.terms = {
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
            "GEMS": "A valuable resources used to draft special FLOORPLANS (the \"cost\" of drafting a particular FLOORPLAN).",
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
        }

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.terms, f, indent=2, ensure_ascii=False)

    def get_term(self, key):
        return self.terms.get(key.upper())
    
class RoomMemory:
    def __init__(self, path="./jsons/room_memory.json"):
        self.path = path
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.rooms = json.load(f)
        else:
            self.rooms = {}

    def add_room(self, room: Room):
        if room.name.upper() in self.rooms:
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
        self.rooms[room.name.upper()] = filtered_data
        self.save()

    def get_room(self, room_name):
        return self.rooms.get(room_name.upper())

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.rooms, f, indent=2, ensure_ascii=False)

    def reset(self):
        self.rooms = {}

class PreviousRunMemory:
    def __init__(self, path: str = "./jsons/previous_run_memory.json"):
        """
            initializes the PreviousRunMemory

                Args:
                    path (str): the path to the previous run memory file
        """
        self.path = path
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.previous_runs: List[Dict[str, Any]] = json.load(f)
        else:
            self.previous_runs: List[Dict[str, Any]] = []

    def add_run(self, day: int, reason: str, stored_item: str = "") -> None:
        """
            adds a run to the previous run memory

                Args:
                    day (int): the day of the run
                    reason (str): the reason for ending the run
                    stored_item (str): the item stored in coat check (optional)
        """
        self.previous_runs.append({
            "day": day,
            "reason": reason,
            "stored_item": stored_item
        })
        self.save()

    def save(self) -> None:
        """
            saves the previous runs to disk
        """
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.previous_runs, f, indent=2, ensure_ascii=False)

    def get_most_recent_run(self) -> Dict[str, Any]:
        """
            gets the most recent run if it exists

                Returns:
                    dict: the most recent run, or an empty dict if none exist
        """
        if self.previous_runs:
            return self.previous_runs[-1]
        return {}