import contextlib
import itertools
import sys
import threading
import time

from game.constants import DIRECTORY


def animate(stop, text="Thinking"):
    """
        Display animated thinking dots in the console

            Args:
                stop: Function that returns True when animation should stop
                text: Text to display before the animated dots
    """
    for i in itertools.cycle(['   ', '.  ', '.. ', '...']):
        if stop():  # Check if we should stop
            break
        sys.stdout.write(f'\r{text}' + i)
        sys.stdout.flush()
        time.sleep(0.5)

def start_animation(text="Thinking"):
    """
        Start an animation thread for displaying thinking dots

            Args:
                text: Text to display before the animated dots

            Returns:
                Tuple containing the thread object and stop function
    """
    stop_thread = threading.Event()
    t = threading.Thread(target=animate, args=(stop_thread.is_set, text))
    t.daemon = True
    t.start()
    return t, stop_thread.set


@contextlib.contextmanager
def thinking_animation(text="Thinking"):
    """
        Context manager for thinking animation that hides the cursor

            Args:
                text: Text to display before the animated dots
    """
    # Hide cursor
    sys.stdout.write('\033[?25l')
    sys.stdout.flush()

    thread, stop = start_animation(text)
    try:
        yield
    finally:
        stop()
        thread.join(timeout=1)
        # Clear the animation line and show cursor again
        sys.stdout.write('\r' + ' ' * (len(text) + 4) + '\r')
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()


def get_color_code(input: str) -> str:
    """
        Get the ANSI color code for a room based on its type from the DIRECTORY
        
            Args:
                input: Name of the room or item to get color code for
            
            Returns:
                ANSI color code string
    """
    # ANSI color codes
    ORANGE = '\033[33m'         # Yellow/Orange
    YELLOW = '\033[93m'         # Bright Yellow
    GREEN = '\033[32m'          # Green
    RED = '\033[31m'            # Red
    BLUE = '\033[34m'           # Blue
    LIGHT_BLUE = '\033[94m'     # Light Blue
    PINK = '\033[95m'           # Pink
    PURPLE = '\033[35m'         # Purple
    BLACK = '\033[90m'          # Gray (using it for black)
    RESET = '\033[0m'           # Reset color
    
    # Check which category the room belongs to in DIRECTORY
    if input.upper() == "GEMS":
        return f"{PINK}{input.upper()}{RESET}"
    elif input.upper() == "KEYS":
        return f"{LIGHT_BLUE}{input.upper()}{RESET}"
    elif input.upper() == "COINS":
        return f"{YELLOW}{input.upper()}{RESET}"
    elif input.upper() == "BLACK":
        return f"{BLACK}{input.upper()}{RESET}"
    elif input.upper() == "BLUE" or input.upper() in DIRECTORY["FLOORPLANS"]["ROOMS"] and input.upper() not in ["ENTRANCE HALL", "THE FOUNDATION", "ANTECHAMBER"]:
        return f"{BLUE}{input.upper()}{RESET}"
    elif input.upper() in DIRECTORY["FLOORPLANS"]["BEDROOMS"]:
        return f"{PURPLE}{input.upper()}{RESET}"
    elif input.upper() in DIRECTORY["FLOORPLANS"]["HALLWAYS"]:
        return f"{ORANGE}{input}{RESET}"
    elif input.upper() in DIRECTORY["FLOORPLANS"]["SHOPS"]:
        return f"{YELLOW}{input}{RESET}"
    elif input.upper() == "YES" or input.upper() in DIRECTORY["FLOORPLANS"]["GREEN ROOMS"]:
        return f"{GREEN}{input}{RESET}"    
    elif input.upper() == "NO" or input.upper() in DIRECTORY["FLOORPLANS"]["RED ROOMS"]:
        return f"{RED}{input}{RESET}"
    else:
        return input.upper()