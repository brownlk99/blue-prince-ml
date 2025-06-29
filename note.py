import hashlib

class Note:
    def __init__(self, title: str = "", content: str = "", found_in_room: str = "", color: str = "", hash: str = ""):
        self.title = title
        self.content = content
        self.found_in_room = found_in_room
        self.color = color
        if hash == "":
            self.hash = self.hash_note()
        else:
            self.hash = hash

    def hash_note(self) -> str:
        """Generate a unique hash for the note based on its content."""
        note_string = f"{self.title}{self.content}{self.found_in_room}{self.color}"
        return hashlib.sha256(note_string.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "content": self.content,
            "found_in_room": self.found_in_room,
            "color": self.color,
            "hash": self.hash
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        return cls(
            title=data["title"],
            content=data["content"],
            found_in_room=data["found_in_room"],
            color=data["color"],
            hash=data["hash"]
        )