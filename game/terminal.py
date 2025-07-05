import time
from typing import List, Dict, Optional, Any, cast

from game.constants import DIRECTORY


class Terminal:
    """
        Base class for all in-game terminals

            Attributes:
                room_name: The name of the room this terminal is in
                commands: List of available commands for this terminal
                network_password: The password required to access the network
                knows_password: Whether the user has successfully logged in
    """
    def __init__(self) -> None:
        """
            Initialize a Terminal instance
        """
        self.room_name = None  # will be set by subclasses
        self.commands = self.get_commands()
        self.network_password = "SWANSONG"
        self.knows_password = False

    def get_commands(self) -> List[str]:
        """
            Return a list of menu command names

                Returns:
                    List of command names available for this terminal
        """
        return ["Login to Network", "Exit"]

    def get_menu_structure(self) -> List[Dict]:
        """
            Return a structured list of menu commands with descriptions and sub-commands

                Returns:
                    List of dictionaries containing command information
        """
        base_menu = [
            {
                "command": "Login to Network",
                "description": "Access the secure network.",
            },
            {
                "command": "Exit",
                "description": "Log out of the terminal.",
            }
        ]

        if self.knows_password:
            base_menu.append({
                "command": "Special Orders",
                "description": "If you would like to get a specific brand of gum or your favorite fruit, the Comissary is now taking Special Orders for all members of the staff.\n(Special Orders can take 1-3 days)"
            })
        return base_menu

    def display_menu(self) -> None:
        """
            Print the menu commands to the console
        """
        print(f"\n{self.room_name} TERMINAL")
        for command, description in self.get_menu_structure():
            print(f"{command}: {description}")

    def login_to_the_network(self, password: str) -> bool:
        """
            Attempt to login to the network with the provided password

                Args:
                    password: The password to attempt login with

                Returns:
                    True if login successful, False otherwise
        """
        if password == self.network_password:
            self.knows_password = True
            return True
        else:
            print("Login failed. Incorrect password.")
            return False
        
    # TODO: maybe this should be an attribute?
    def get_special_order_items(self) -> List[str]:
        """
            Return a list of special order items available

                Returns:
                    List of special order item names
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
    
    def to_dict(self) -> Dict[str, Any]:
        """
            Convert the Terminal instance to a dictionary representation

                Returns:
                    Dictionary representation of the terminal
        """
        return {
            "commands": self.commands,
            "network_password": self.network_password,
            "knows_password": self.knows_password
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Terminal':
        """
            Create a Terminal instance from a dictionary representation

                Args:
                    data: Dictionary containing terminal data

                Returns:
                    Terminal instance created from the data
        """
        terminal = cls()  # no parameters needed
        terminal.knows_password = data.get("knows_password", False)
        return terminal


class SecurityTerminal(Terminal):
    """
        Security terminal with estate inventory and security controls

            Attributes:
                estate_inventory: Dictionary tracking estate inventory items
                security_level: Current security level setting
                offline_mode: Mode for security doors when power is lost
                keycard_system: Status of the keycard system
    """
    def __init__(self) -> None:
        """
            Initialize a SecurityTerminal instance
        """
        super().__init__()
        self.room_name = "SECURITY"
        self.estate_inventory = {"FRUIT": 0, "GEMS": 0, "KEYS": 0, "COINS": 0}
        self.security_level = "MEDIUM"
        self.offline_mode = "LOCKED"
        self.keycard_system = "OPERATIONAL"     # TODO: interaction with the UTILITY ROOM

    def get_commands(self) -> List[str]:
        """
            Return list of available commands for security terminal

                Returns:
                    List of command names available for this terminal
        """
        return super().get_commands() + [
            "View Estate Inventory",
            "Alter Security Level",
            "Alter Mode"
        ]

    def get_menu_structure(self) -> List[Dict]:
        """
            Return structured menu with security-specific commands

                Returns:
                    List of dictionaries containing command information
        """
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
            Set the security level for the estate

                Args:
                    level: The security level to set (LOW, MEDIUM, HIGH)
        """
        valid_levels = ["LOW", "MEDIUM", "HIGH"]
        if level.upper() in valid_levels:
            self.security_level = level.upper()
            print(f"Security level set to {self.security_level}.")
        else:
            print("Invalid security level.")

    def set_mode(self, mode: str) -> None:
        """
            Set the offline mode for security doors

                Args:
                    mode: The mode to set (LOCKED, UNLOCKED)
        """
        valid_modes = ["LOCKED", "UNLOCKED"]
        if mode.upper() in valid_modes:
            self.offline_mode = mode.upper()
            print(f"Offline mode set to {self.offline_mode}.")
        else:
            print("Invalid offline mode.")

    def to_dict(self) -> Dict[str, Any]:
        """
            Convert the SecurityTerminal instance to a dictionary representation

                Returns:
                    Dictionary representation of the security terminal
        """
        data = super().to_dict()
        data.update({
            "estate_inventory": self.estate_inventory,
            "security_level": self.security_level,
            "offline_mode": self.offline_mode,
            "keycard_system": self.keycard_system
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityTerminal':
        """
            Create a SecurityTerminal instance from a dictionary representation

                Args:
                    data: Dictionary containing security terminal data

                Returns:
                    SecurityTerminal instance created from the data
        """
        terminal = cast('SecurityTerminal', super().from_dict(data))
        terminal.estate_inventory = data.get("estate_inventory", {})
        terminal.security_level = data.get("security_level", "MEDIUM")
        terminal.offline_mode = data.get("offline_mode", "LOCKED")
        terminal.keycard_system = data.get("keycard_system", "OPERATIONAL")
        return terminal
    
    def __str__(self) -> str:
        """
            Return a string representation of the SecurityTerminal

                Returns:
                    String representation showing the security terminal's properties
        """
        return super().__str__() + f", estate_inventory={self.estate_inventory}, security_level={self.security_level}, offline_mode={self.offline_mode}, keycard_system={self.keycard_system}"
    

class OfficeTerminal(Terminal):
    """
        Office terminal with payroll and gold distribution capabilities

            Attributes:
                payroll_ran: Whether payroll has been run
                gold_spread: Whether gold has been spread in the estate
    """
    def __init__(self) -> None:
        """
            Initialize an OfficeTerminal instance
        """
        super().__init__()
        self.room_name = "OFFICE"
        self.payroll_ran = False
        self.gold_spread = False

    def get_commands(self) -> List[str]:
        """
            Return list of available commands for office terminal

                Returns:
                    List of command names available for this terminal
        """
        return super().get_commands() + ["Run Payroll", "Spread Gold in Estate"]

    def get_menu_structure(self) -> List[Dict]:
        """
            Return structured menu with office-specific commands

                Returns:
                    List of dictionaries containing command information
        """
        return super().get_menu_structure() + [
            {
                "command": "Run Payroll",
                "description": "After running this process, checks will be placed in each staff member's room. This includes each Servant's Quarter and Maid's Chamber currently on the estate.",
            },
            {
                "command": "Spread Gold in Estate",
                "description": "The Office can facilitate a modest distribution of coins withdrawn from the Staff Incentives program.\nThese coins are \"spread\" (distributed in a number of rooms currently active) throughout the estate.",
            }
        ]

    def to_dict(self) -> Dict[str, Any]:
        """
            Convert the OfficeTerminal instance to a dictionary representation

                Returns:
                    Dictionary representation of the office terminal
        """
        data = super().to_dict()
        data.update({
            "payroll_ran": self.payroll_ran,
            "gold_spread": self.gold_spread
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OfficeTerminal':
        """
            Create an OfficeTerminal instance from a dictionary representation

                Args:
                    data: Dictionary containing office terminal data

                Returns:
                    OfficeTerminal instance created from the data
        """
        terminal = cast('OfficeTerminal', super().from_dict(data))
        terminal.payroll_ran = data.get("payroll_ran", False)
        terminal.gold_spread = data.get("gold_spread", False)
        return terminal
    
    def __str__(self) -> str:
        """
            Return a string representation of the OfficeTerminal

                Returns:
                    String representation showing the office terminal's properties
        """
        return super().__str__() + f", payroll_ran={self.payroll_ran}, gold_spread={self.gold_spread}"


class LabTerminal(Terminal):
    """
        Laboratory terminal with experimental house feature capabilities

            Attributes:
                experimental_house_feature: Dictionary containing experimental feature data
    """
    def __init__(self) -> None:
        """
            Initialize a LabTerminal instance
        """
        super().__init__()
        self.room_name = "LABORATORY"
        self.experimental_house_feature = {}

    def get_commands(self) -> List[str]:
        """
            Return list of available commands for lab terminal

                Returns:
                    List of command names available for this terminal
        """
        return super().get_commands() + ["Experiment Setup", "Pause Experiment"]
    
    def get_menu_structure(self) -> List[Dict]:
        """
            Return structured menu with lab-specific commands

                Returns:
                    List of dictionaries containing command information
        """
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

    def set_experimental_house_feature(self, dict_input: Optional[dict] = None) -> None:
        """
            Set the experimental house feature

                Args:
                    dict_input: Dictionary containing experimental feature data
        """
        if dict_input:
            self.experimental_house_feature = dict_input
        else:
            self.experimental_house_feature = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
            Convert the LabTerminal instance to a dictionary representation

                Returns:
                    Dictionary representation of the lab terminal
        """
        data = super().to_dict()
        data.update({
            "experimental_house_feature": self.experimental_house_feature
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LabTerminal':
        """
            Create a LabTerminal instance from a dictionary representation

                Args:
                    data: Dictionary containing lab terminal data

                Returns:
                    LabTerminal instance created from the data
        """
        terminal = cast('LabTerminal', super().from_dict(data))
        terminal.experimental_house_feature = data.get("experimental_house_feature", {})
        return terminal
    
    def __str__(self) -> str:
        """
            Return a string representation of the LabTerminal

                Returns:
                    String representation showing the lab terminal's properties
        """
        return super().__str__() + f", experimental_house_feature={self.experimental_house_feature}"


class ShelterTerminal(Terminal):
    """
        Shelter terminal with time lock and radiation monitoring capabilities

            Attributes:
                time_lock_engaged: Whether the time lock safe is currently engaged
                radiation_level: Current radiation level reading
    """
    def __init__(self) -> None:
        """
            Initialize a ShelterTerminal instance
        """
        super().__init__()
        self.room_name = "SHELTER"
        self.time_lock_engaged = True
        self.radiation_level = "NORMAL"

    def get_commands(self) -> List[str]:
        """
            Return list of available commands for shelter terminal

                Returns:
                    List of command names available for this terminal
        """
        return super().get_commands() + ["Time Lock Safe", "Radiation Monitor"]
    
    def get_menu_structure(self) -> List[Dict]:
        """
            Return structured menu with shelter-specific commands

                Returns:
                    List of dictionaries containing command information
        """
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
    
    def set_time_lock_safe(self) -> None:
        """
            Set the time lock for the safe in the shelter
        """
        while True:
            try:
                unlock_time = input("Enter unlock date and time (MM HH:MM): ")
                # here you would validate the date and time format
                print(f"Time Lock Safe set to unlock at {unlock_time}.")
                self.time_lock_engaged = False
                break
            except ValueError:
                print("Invalid date/time format. Please try again.")

    def take_radiation_reading(self) -> None:
        """
            Simulate taking a radiation reading
        """
        # this is a placeholder for actual radiation reading logic
        # TODO: implement actual radiation reading logic
        print("Taking radiation reading...")

    def to_dict(self) -> Dict[str, Any]:
        """
            Convert the ShelterTerminal instance to a dictionary representation

                Returns:
                    Dictionary representation of the shelter terminal
        """
        data = super().to_dict()
        data.update({
            "time_lock_engaged": self.time_lock_engaged,
            "radiation_level": self.radiation_level
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ShelterTerminal':
        """
            Create a ShelterTerminal instance from a dictionary representation

                Args:
                    data: Dictionary containing shelter terminal data

                Returns:
                    ShelterTerminal instance created from the data
        """
        terminal = cast('ShelterTerminal', super().from_dict(data))
        terminal.time_lock_engaged = data.get("time_lock_engaged", True)
        terminal.radiation_level = data.get("radiation_level", "NORMAL")
        return terminal
    
    def __str__(self) -> str:
        """
            Return a string representation of the ShelterTerminal

                Returns:
                    String representation showing the shelter terminal's properties
        """
        return super().__str__() + f", time_lock_engaged={self.time_lock_engaged}, radiation_level={self.radiation_level}"
