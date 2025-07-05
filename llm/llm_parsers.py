import json
from typing import Dict, Any

from llm.llm_agent import BluePrinceAgent


def _parse_json_response(response: str) -> Dict[str, Any]:
    """
        Helper function to parse JSON response with consistent error handling

            Args:
                response: The JSON response string to parse

            Returns:
                Parsed JSON data as dictionary

            Raises:
                ValueError: If JSON parsing fails
    """
    response = response.replace("```json", "").replace("```", "")
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")


def parse_action_response(response: str) -> Dict[str, str]:
    """
        Parse the action response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing action and explanation
    """
    data = _parse_json_response(response)
    action = data.get("action", "").strip()
    explanation = data.get("explanation", "").strip()
    return {"action": action, "explanation": explanation}


def parse_move_response(response: str) -> Dict[str, Any]:
    """
        Parse the move response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing target room, path, planned action, and explanation
    """
    data = _parse_json_response(response)
    target_room = data.get("target_room", "").strip().upper()
    path = data.get("path", [])
    planned_action = data.get("planned_action", "").strip()
    explanation = data.get("explanation", "").strip()
    return {
        "target_room": target_room,
        "path": path,
        "planned_action": planned_action,  
        "explanation": explanation
    }


def parse_door_opening_response(response: str, agent: BluePrinceAgent) -> Dict[str, str]:
    """
        Parse the door opening response from the LLM

            Args:
                response: The JSON response string from the LLM
                agent: The BluePrinceAgent instance to update

            Returns:
                Dictionary containing door direction, special item, and explanation
    """
    data = _parse_json_response(response)
    door_direction = data.get("door_direction", "").strip().upper()[0]
    special_item = data.get("special_item", "NONE").strip().upper()
    explanation = data.get("explanation", "").strip()
    
    # set the previously chosen room and door for drafting
    agent.previously_chosen_room = agent.game_state.current_room.name if agent.game_state.current_room else ""
    agent.previously_chosen_door = door_direction
    
    return {
        "door_direction": door_direction,
        "special_item": special_item,
        "explanation": explanation
    }


def parse_purchase_response(response: str) -> Dict[str, Any]:
    """
        Parse the purchase response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing item, quantity, and explanation
    """
    data = _parse_json_response(response)
    item = data.get("item", "").strip().upper()
    quantity = data.get("quantity", 0)
    explanation = data.get("explanation", "").strip()
    return {
        "item": item,
        "quantity": quantity,
        "explanation": explanation
    }


def parse_drafting_response(response: str) -> Dict[str, Any]:
    """
        Parse the drafting response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing either redraw action or room selection data
    """
    data = _parse_json_response(response)
    if data.get("action", "").strip().upper() == "REDRAW":
        return {
            "action": "REDRAW",
            "type": data.get("type", "").strip().upper(),
            "explanation": data.get("explanation", "").strip()
        }
    else:
        room_name = data.get("room", "").strip().upper()
        explanation = data.get("explanation", "").strip()
        enter = data.get("enter", "").strip().upper()
        return {
            "room": room_name,
            "explanation": explanation,
            "enter": enter
        }


def parse_parlor_response(response: str) -> Dict[str, str]:
    """
        Parse the parlor puzzle response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing box choice and explanation
    """
    data = _parse_json_response(response)
    box = data.get("box", "").strip().upper()
    explanation = data.get("explanation", "").strip()
    return {
        "box": box,
        "explanation": explanation
    }


def parse_terminal_response(response: str) -> Dict[str, str]:
    """
        Parse the terminal response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing command and explanation
    """
    data = _parse_json_response(response)
    command = data.get("command", "").strip()
    explanation = data.get("explanation", "").strip()
    return {
        "command": command,
        "explanation": explanation
    }


def parse_password_guess_response(response: str) -> Dict[str, str]:
    """
        Parse the password guess response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing password and explanation
    """
    data = _parse_json_response(response)
    password = data.get("password", "").strip().upper()
    explanation = data.get("explanation", "").strip()
    return {
        "password": password,
        "explanation": explanation
    }

def parse_special_order_response(response: str) -> Dict[str, str]:
    """
        Parse the special order response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing item and explanation
    """
    data = _parse_json_response(response)
    item = data.get("item", "NONE").strip().upper()
    explanation = data.get("explanation", "").strip()
    return {
        "item": item,
        "explanation": explanation
    }

def parse_security_level_response(response: str) -> Dict[str, str]:
    """
        Parse the security level response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing security level and explanation
    """
    data = _parse_json_response(response)
    security_level = data.get("security_level", "").strip()
    explanation = data.get("explanation", "").strip()
    return {
        "security_level": security_level,
        "explanation": explanation
    }


def parse_mode_response(response: str) -> Dict[str, str]:
    """
        Parse the mode response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing mode and explanation
    """
    data = _parse_json_response(response)
    mode = data.get("mode", "").strip()
    explanation = data.get("explanation", "").strip()

    return {
        "mode": mode,
        "explanation": explanation
    }


def parse_lab_experiment_response(response: str) -> Dict[str, str]:
    """
        Parse the lab experiment response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing either action or experiment data with explanation
    """
    data = _parse_json_response(response)
    if data.get("action", ""):
        action = data.get("action", "").strip().upper()
        explanation = data.get("explanation", "").strip()
        return {
            "action": action,
            "explanation": explanation
        }
    else:
        cause = data.get("cause", "").strip()
        effect = data.get("effect", "").strip()
        explanation = data.get("explanation", "").strip()
        return {
            "cause": cause,
            "effect": effect,
            "explanation": explanation
        }


def parse_coat_check_response(response: str) -> Dict[str, str]:
    """
        Parse the coat check response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing item and explanation
    """
    data = _parse_json_response(response)
    item = data.get("item", "").strip()
    explanation = data.get("explanation", "").strip()
    return {
        "item": item,
        "explanation": explanation
    }


def parse_secret_passage_response(response: str) -> Dict[str, str]:
    """
        Parse the secret passage response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                Dictionary containing room type and explanation
    """
    data = _parse_json_response(response)
    room_type = data.get("room_type", "").strip().upper()
    explanation = data.get("explanation", "").strip()
    return {
        "room_type": room_type,
        "explanation": explanation
    }


def parse_note_title_response(response: str) -> str:
    """
        Parse the note title response from the LLM

            Args:
                response: The JSON response string from the LLM

            Returns:
                The generated title text
    """
    data = _parse_json_response(response)
    title = data.get("title", "").strip()
    return title 