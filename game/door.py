from typing import Optional


class Door:
    """
        Represents a door in the game with properties for connectivity, locking, and security

            Attributes:
                leads_to: The room or location this door leads to
                locked: Whether the door is currently locked
                is_security: Whether this is a security door requiring special access
                orientation: The direction the door faces (N, S, E, W)
    """
    def __init__(self, leads_to: str = "?", locked: str = "?", is_security: str = "?", orientation: str = "?") -> None:
        """
            Initialize a Door instance

                Args:
                    leads_to: The room or location this door leads to
                    locked: Whether the door is currently locked
                    is_security: Whether this is a security door requiring special access
                    orientation: The direction the door faces (N, S, E, W)
        """
        self.leads_to = leads_to            # room object
        self.locked = locked                # is the door currently locked
        self.is_security = is_security      # true if this is a security door
        self.orientation = orientation      # NSWE

    def to_dict(self) -> dict:
        """
            Convert the Door instance to a dictionary representation

                Returns:
                    A dictionary representation of the door
        """
        return {
            "leads_to": self.leads_to,
            "locked": self.locked,
            "is_security": self.is_security,
            "orientation": self.orientation
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Door':
        """
            Create a Door instance from a dictionary representation

                Args:
                    data: A dictionary containing door data

                Returns:
                    A Door instance created from the dictionary data
        """
        return cls(
            leads_to=data.get("leads_to", "?"),
            locked=data.get("locked", "?"),
            is_security=data.get("is_security", "?"),
            orientation=data.get("orientation", "?")
        )
    
    def __str__(self) -> str:
        """
            Return a string representation of the Door

                Returns:
                    A string representation showing the door's properties
        """
        return f"{self.orientation} - leads_to={self.leads_to}, locked={self.locked}, is_security={self.is_security}"
