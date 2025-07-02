"""
Decorators for common CLI patterns.
"""

from functools import wraps
import traceback
from typing import Any, Callable, TypeVar

from capture.resources import capture_resources
from capture.vision_utils import get_current_room

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


def auto_save(func: F) -> F:
    """Decorator that automatically saves game state after command execution."""
    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = func(self, *args, **kwargs)
        self.agent.game_state.save_to_file('./jsons/current_run.json')
        return result
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