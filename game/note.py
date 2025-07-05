import hashlib


class Note:
    """
        Represents a note found in the game with content and metadata

            Attributes:
                title: The title of the note
                content: The main content text of the note
                found_in_room: The room where the note was found
                color: The color associated with the note
                hash: A unique identifier for the note based on its content
    """
    def __init__(self, title: str = "", content: str = "", found_in_room: str = "", color: str = "", hash: str = "") -> None:
        """
            Initialize a Note instance

                Args:
                    title: The title of the note
                    content: The main content text of the note
                    found_in_room: The room where the note was found
                    color: The color associated with the note
                    hash: A unique identifier for the note, generated if not provided
        """
        self.title = title
        self.content = content
        self.found_in_room = found_in_room
        self.color = color
        if hash == "":
            self.hash = self.hash_note()
        else:
            self.hash = hash

    def hash_note(self) -> str:
        """
            Generate a unique hash for the note based on its content

                Returns:
                    A unique hash string for the note
        """
        note_string = f"{self.title}{self.content}{self.found_in_room}{self.color}"
        return hashlib.sha256(note_string.encode()).hexdigest()

    def to_dict(self) -> dict:
        """
            Convert the Note instance to a dictionary representation

                Returns:
                    A dictionary representation of the note
        """
        return {
            "title": self.title,
            "content": self.content,
            "found_in_room": self.found_in_room,
            "color": self.color,
            "hash": self.hash
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        """
            Create a Note instance from a dictionary representation

                Args:
                    data: A dictionary containing note data

                Returns:
                    A Note instance created from the dictionary data
        """
        return cls(
            title=data["title"],
            content=data["content"],
            found_in_room=data["found_in_room"],
            color=data["color"],
            hash=data["hash"]
        )