"""
Decorators for common CLI patterns.
"""

from functools import wraps
import traceback
from typing import Any, Callable, TypeVar

from capture.resources import capture_resources
from capture.vision_utils import get_current_room
from game.room import CoatCheck, Laboratory, Office, PuzzleRoom, SecretPassage, Security, Shelter, ShopRoom, UtilityCloset

F = TypeVar('F', bound=Callable[..., Any])


def requires_current_room(func: F) -> F:
    """Decorator that ensures current room is set before executing command."""
    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> bool:
        self.agent.game_state.current_room = get_current_room(self.reader, self.agent.game_state.house)
        if not self.agent.game_state.current_room:
            print("Could not determine the current room")
            return False
        return func(self, *args, **kwargs)
    return wrapper  # type: ignore

def capture_resources_first(func: F) -> F:
    """Decorator that captures resources before executing command."""
    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        current_resources = capture_resources(self.google_client, self.agent.game_state.resources)
        self.agent.game_state.resources.update(current_resources)
        self.agent.game_state.edit_resources()
        return func(self, *args, **kwargs)
    return wrapper  # type: ignore


def handle_command_safely(func: F) -> F:
    """Decorator that provides error handling for commands."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> bool:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error executing command: {e}")
            traceback.print_exc()
            return False
    return wrapper  # type: ignore

def auto_save(func: F) -> F:
    """Decorator that automatically saves game state after command execution."""
    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = func(self, *args, **kwargs)
        self.agent.game_state.save()
        return result
    return wrapper  # type: ignore

def _requires_room_type(*required_types: type) -> Callable[[F], F]:
    """Decorator that ensures current room is one of the specified room classes."""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> bool:
            if not self.agent.game_state.current_room:
                print("No current room available.")
                return False
            
            if not isinstance(self.agent.game_state.current_room, required_types):
                type_names = [t.__name__ for t in required_types]
                current_type = type(self.agent.game_state.current_room).__name__
                if len(type_names) == 1:
                    print(f"Current room is not a {type_names[0]} (currently {current_type}).")
                else:
                    print(f"Current room must be one of: {', '.join(type_names)} (currently {current_type}).")
                return False
            
            return func(self, *args, **kwargs)
        return wrapper  # type: ignore
    return decorator

# Specific room type decorators for common cases
def requires_shop_room(func: F) -> F:
    """Decorator that ensures current room is a ShopRoom."""
    return _requires_room_type(ShopRoom)(func)

def requires_puzzle_room(func: F) -> F:
    """Decorator that ensures current room is a PuzzleRoom."""
    return _requires_room_type(PuzzleRoom)(func)

def requires_secret_passage(func: F) -> F:
    """Decorator that ensures current room is a SecretPassage."""
    return _requires_room_type(SecretPassage)(func)

def requires_coat_check(func: F) -> F:
    """Decorator that ensures current room is a CoatCheck."""
    return _requires_room_type(CoatCheck)(func)

def requires_utility_closet(func: F) -> F:
    """Decorator that ensures current room is a UtilityCloset."""
    return _requires_room_type(UtilityCloset)(func)

def requires_security(func: F) -> F:
    """Decorator that ensures current room is a Security."""
    return _requires_room_type(Security)(func)

def requires_office(func: F) -> F:
    """Decorator that ensures current room is an Office."""
    return _requires_room_type(Office)(func)

def requires_laboratory(func: F) -> F:
    """Decorator that ensures current room is a Laboratory."""
    return _requires_room_type(Laboratory)(func)

def requires_shelter(func: F) -> F:
    """Decorator that ensures current room is a Shelter."""
    return _requires_room_type(Shelter)(func)