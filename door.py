class Door:
    def __init__(self, leads_to="?", locked="?", is_security="?", orientation="?"):
        self.leads_to = leads_to            # Room object
        self.locked = locked                # Is the door currently locked?
        self.is_security = is_security      # True if this is a security door
        self.orientation = orientation      # NSWE


    def to_dict(self) -> dict:
        return {
            "leads_to": self.leads_to,
            "locked": self.locked,
            "is_security": self.is_security,
            "orientation": self.orientation
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            leads_to=data.get("leads_to", "?"),
            locked=data.get("locked", "?"),
            is_security=data.get("is_security", "?"),
            orientation=data.get("orientation", "?")
        )
    
    def __str__(self):
        return f"Door(orientation={self.orientation}, leads_to={self.leads_to}, locked={self.locked}, is_security={self.is_security})"
