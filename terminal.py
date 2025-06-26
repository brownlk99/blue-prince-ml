import time
from typing import List, Dict

class Terminal:
    """
        Base class for all in-game terminals.
    """
    def __init__(self):
        self.room_name = None  # Will be set by subclasses
        self.commands = self.get_commands()
        self.network_password = "SWANSONG"
        self.knows_password = False

    def get_commands(self) -> List[str]:
        """
            Return a list of menu command names.
        """
        return ["Login to Network", "Exit"]

    def get_menu_structure(self) -> List[Dict]:
        """
            Return a structured list of menu commands with descriptions and sub-commands.
        """
        return [
            {
                "command": "Login to Network",
                "description": "Access the secure network.",
            },
            {
                "command": "Exit",
                "description": "Log out of the terminal.",
            }
        ]

    def display_menu(self) -> None:
        """
            Print the menu commands to the console.
        """
        print(f"\n{self.room_name} TERMINAL")
        for command, description in self.get_menu_structure():
            print(f"{command}: {description}")

    def login_to_the_network(self, password: str) -> bool:
        """
            Attempt to login to the network with the provided password.
        """
        if password == self.network_password:
            print("Login successful.")
            self.knows_password = True
            return True
        else:
            print("Login failed. Incorrect password.")
            return False
        
    def logged_in_menu(self) -> None:
        if self.knows_password:
            self.get_menu_structure().append({
                "command": "SPECIAL ORDERS",
                "description": "If you would like to get a specific brand of gum or your favorite fruit, the Comissary is now taking Special Orders for all members of the staff.\n(Special Orders can take 1-3 days)"
            })

    #TODO: maybe this should be an attribute?
    def get_special_order_items(self) -> List[str]:
        """
            Return a list of special order items available.
        """
        return [
            "BRASS COMPASS",
            "MAGNIFYING GLASS",
            "METAL DETECTOR",
            "RUNNING SHOES",
            "SHOVEL",
            "SLEEPING MASK",
            "SLEDGE HAMMER"
        ]
    
    def to_dict(self):
        return {
            "commands": self.commands,
            "network_password": self.network_password,
            "knows_password": self.knows_password
        }

    @classmethod
    def from_dict(cls, data):
        terminal = cls()  # No parameters needed
        terminal.knows_password = data.get("knows_password", False)
        return terminal

class SecurityTerminal(Terminal):
    def __init__(self):
        super().__init__()
        self.room_name = "SECURITY"
        self.estate_inventory = {"FRUIT": 0, "GEMS": 0, "KEYS": 0, "COINS": 0}
        self.security_level = "MEDIUM"
        self.offline_mode = "LOCKED"
        self.keycard_system = "OPERATIONAL"     #TODO: interaction with the UTILITY ROOM

    def get_commands(self) -> List[str]:
        return super().get_commands() + [
            "View Estate Inventory",
            "Alter Security Level",
            "Alter Mode"
        ]

    def get_menu_structure(self) -> List[Dict]:
        return super().get_menu_structure() + [
            {
                "command": "View Estate Inventory",
                "description": "The following is a detailed list of the items currently in the house that have yet to be collected. This list will be updated as new rooms are added.",
            },
            {
                "command": "Alter Security Level",
                "description": "The SECURITY LEVEL determines the amount of Keycard Security Doors that will be deployed in your estate.\n E.g. you should expect to see 1 or 2 security doors with a LOW setting and 5 or 6 with a HIGH setting.",
            },
            {
                "command": "Alter Mode",
                "description": "This mode determines the default setting the Security Doors will be set to if power is lost, (during a black-out for example.)\nAs a general safety rule, OFFLINE MODE should be set to UNLOCKED if any staff are working on the estate.",
            }
        ]
    
    def set_estate_inventory(self) -> None:
        """
            Allow the user to select an inventory item to edit, set its amount, or quit

                Returns:
                    None
        """
        while True:
            print("\nEstate Inventory:")
            for item, amount in self.estate_inventory.items():
                print(f"  {item}: {amount}")
            print("\nType the item name to edit, or 'q' to quit.")
            choice = input("Select item: ").strip().upper()
            if choice == 'Q':
                break
            if choice in self.estate_inventory:
                while True:
                    try:
                        value = int(input(f"Enter new amount for {choice}: "))
                        if value < 0:
                            print("Amount cannot be negative. Try again.")
                            time.sleep(1)
                            continue
                        self.estate_inventory[choice] = value
                        print(f"{choice} updated to {value}.")
                        break
                    except ValueError:
                        print("Please enter a valid integer.")
                        time.sleep(1)
            else:
                print("Invalid item. Please choose from the list.")
                time.sleep(1)
    
    def set_security_level(self, level: str) -> None:
        """
            Set the security level for the estate.
        """
        valid_levels = ["LOW", "MEDIUM", "HIGH"]
        if level.upper() in valid_levels:
            self.security_level = level.upper()
            print(f"Security level set to {self.security_level}.")
        else:
            print("Invalid security level.")

    def set_mode(self, mode: str) -> None:
        """
            Set the offline mode for security doors.
        """
        valid_modes = ["LOCKED", "UNLOCKED"]
        if mode.upper() in valid_modes:
            self.offline_mode = mode.upper()
            print(f"Offline mode set to {self.offline_mode}.")
        else:
            print("Invalid offline mode.")

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "estate_inventory": self.estate_inventory,
            "security_level": self.security_level,
            "offline_mode": self.offline_mode,
            "keycard_system": self.keycard_system
        })
        return data

    @classmethod
    def from_dict(cls, data):
        terminal = cls()  # No parameters needed
        terminal.knows_password = data.get("knows_password", False)
        terminal.estate_inventory = data.get("estate_inventory", {})
        terminal.security_level = data.get("security_level", "MEDIUM")
        terminal.offline_mode = data.get("offline_mode", "LOCKED")
        terminal.keycard_system = data.get("keycard_system", "OPERATIONAL")
        return terminal
    
    def __str__(self):
        return super().__str__() + f", estate_inventory={self.estate_inventory}, security_level={self.security_level}, offline_mode={self.offline_mode}, keycard_system={self.keycard_system}"
    

class OfficeTerminal(Terminal):
    #TODO: this needs to be implemented
    def __init__(self):
        super().__init__()
        self.room_name = "OFFICE"
        self.office_equipment = {}

    def get_commands(self):
        return super().get_commands() + ["Check Inventory", "Purchase Item", "View Office Logs"]

class LabTerminal(Terminal):
    def __init__(self):
        super().__init__()
        self.room_name = "LABORATORY"
        self.experimental_house_feature = {}

    def get_commands(self):
        return super().get_commands() + ["Experiment Setup", "Pause Experiment"]
    
    def get_menu_structure(self):
         return super().get_menu_structure() + [
            {
                "command": "Run Experiment Setup",
                "description": "In the Laboratory, you are free to experiment by testing and combining different mechanics to create an original and unique House Feature that will last until the end of the day.",
            },
            {
                "command": "Pause Experiment",
                "description": "If you wish to take a break from your experiment, you can pause it and resume later.",
            }
        ]

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "experimental_house_feature": self.experimental_house_feature
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        terminal = cls()  # No parameters needed
        terminal.knows_password = data.get("knows_password", False)
        terminal.experimental_house_feature = data.get("experimental_house_feature", {})
        return terminal
    
    def __str__(self):
        return super().__str__() + f", experimental_house_feature={self.experimental_house_feature}"

class ShelterTerminal(Terminal):
    def __init__(self):
        super().__init__()
        self.room_name = "SHELTER"
        self.time_lock_engaged = True
        self.radiation_level = "NORMAL"

    def get_commands(self):
        return super().get_commands() + ["Time Lock Safe", "Radiation Monitor"]
    
    def get_menu_structure(self):
        return super().get_menu_structure() + [
            {
                "command": "Time Lock Safe",
                "description": "The Shelter's Time-Lock Safe can be accessed by setting an 'UNLOCK DATE and TIME'.\nYou can use any date and time as long as it's at least one hour in the future.\n Once unlocked, the Time-Lock Safe will remain open for 4 hours.",
            },
            {
                "command": "Radiation Monitor",
                "description": "A measurement of the RADIATION levels detected in the house and surrounding grounds. (These readings are often spiked by the experiments conducted in Mt. Holly's laboratory.}\n If the reading is 12 uSv or higher, emergency protocol will initiate and all doors in the house will automatically unlock.)",
            }
        ]
    
    def set_time_lock_safe(self):
        """
            Set the time lock for the safe in the shelter.
        """
        while True:
            try:
                unlock_time = input("Enter unlock date and time (MM HH:MM): ")
                # Here you would validate the date and time format
                print(f"Time Lock Safe set to unlock at {unlock_time}.")
                self.time_lock_engaged = False
                break
            except ValueError:
                print("Invalid date/time format. Please try again.")

    def take_radiation_reading(self):
        """
            Simulate taking a radiation reading.
        """
        # This is a placeholder for actual radiation reading logic
        #TODO: Implement actual radiation reading logic
        print("Taking radiation reading...")

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "time_lock_engaged": self.time_lock_engaged,
            "radiation_level": self.radiation_level
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        terminal = cls()  # No parameters needed
        terminal.knows_password = data.get("knows_password", False)
        terminal.time_lock_engaged = data.get("time_lock_engaged", True)
        terminal.radiation_level = data.get("radiation_level", "NORMAL")
        return terminal
    
    def __str__(self):
        return super().__str__() + f", time_lock_engaged={self.time_lock_engaged}, radiation_level={self.radiation_level}"
