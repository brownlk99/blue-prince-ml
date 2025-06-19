import hashlib

class Note:
    def __init__(self, title: str = "", content: str = "", found_in_room: str = "", color: str = ""):
        self.title = title
        self.content = content
        self.found_in_room = found_in_room
        self.color = color

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "content": self.content,
            "found_in_room": self.found_in_room,
            "color": self.color
        }
    
    def hash_note(self) -> str:
        """Generate a unique hash for the note based on its content."""
        note_string = f"{self.title}{self.content}{self.found_in_room}{self.color}"
        return hashlib.sha256(note_string.encode()).hexdigest()

    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        return cls(
            title=data["title"],
            content=data["content"],
            found_in_room=data["found_in_room"],
            color=data["color"]
        )