"""
Refactored main.py using the CLI module structure.
"""

import argparse
import os
import warnings

import easyocr
from google.cloud import vision

from game.game_state import GameState
from llm.llm_agent import BluePrinceAgent
from cli.menu import CliMenu
from utils import thinking_animation


warnings.filterwarnings("ignore", category=UserWarning, module="torch.utils.data.dataloader")



def main(day, load, verbose, editor_path, model_name, use_utility_model):
    """Main function - now much simpler and cleaner."""
    with thinking_animation("Initializing Blue Prince ML"):
        # Initialize game state
        game_state = None
        if load:
            game_state = GameState.load_from_file(load)
        else:
            game_state = GameState(current_day=day)
        
        # Initialize clients and agent
        google_client = vision.ImageAnnotatorClient()
        reader = easyocr.Reader(['en'], gpu=False)
        agent = BluePrinceAgent(game_state, verbose, model_name, use_utility_model)

        # Clear memory if a completely fresh run
        if agent.game_state.day == 1 and not load:
            agent.room_memory.reset()
            agent.term_memory.reset()
            agent.decision_memory.reset()
        elif load:
            # Search through decisions in reverse order (most recent first)
            for decision in reversed(agent.decision_memory.data):
                # Check if this decision contains door opening data
                if isinstance(decision, dict) and "door_direction" in decision:
                    # This is a door opening decision - use current room from game state
                    agent.previously_chosen_room = agent.game_state.current_room.name if agent.game_state.current_room else ""
                    agent.previously_chosen_door = decision["door_direction"]
                    break
            
            # If no door opening decision found, keep current values or set defaults
            if not agent.previously_chosen_room:
                print("No previous door opening decision found in memory.")

    # Create and run the game menu
    menu = CliMenu(agent, google_client, reader, editor_path, verbose)
    menu.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--load', '-l', type=str, help='Path to saved game state JSON')
    parser.add_argument('--day', '-d', type=int, required=True, help='Day/run number for this session')
    parser.add_argument('--model', '-m', type=str, default="openai:o4-mini", help='Model to use for LLM (default: o4-mini)')
    parser.add_argument('--use_utility_model', '-u', action='store_true', help='Use utility model for LLM (default: False)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show full LLM prompts')
    parser.add_argument('--editor', '-e', type=str, default=os.environ.get('EDITOR_PATH'), help='Path to text editor (default: from EDITOR_PATH env var)')
    args = parser.parse_args()

    main(args.day, args.load, args.verbose, args.editor, args.model, args.use_utility_model) 