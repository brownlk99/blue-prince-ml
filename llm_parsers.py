import json

from llm_agent import BluePrinceAgent


def _parse_json_response(response: str):
    """Helper function to parse JSON response with consistent error handling"""
    response = response.replace("```json", "").replace("```", "")
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse LLM response as JSON: {e}\nResponse was:\n{response}")


def parse_action_response(response: str):
    """Parse the action response from the LLM"""
    data = _parse_json_response(response)
    action = data.get("action", "").strip()
    explanation = data.get("explanation", "").strip()
    return {"action": action, "explanation": explanation}


def parse_door_exploration_response(response: str, agent: BluePrinceAgent):
    """Parse the door exploration response from the LLM"""
    data = _parse_json_response(response)
    room_name = data.get("target_room", "").strip().upper()
    door_dir = data.get("final_door", "").strip().upper()[0]
    path = data.get("path", [])
    special_item = data.get("special_item", "NONE").strip().upper()
    explanation = data.get("explanation", "").strip()   
    agent.previously_chosen_room = room_name
    agent.previously_chosen_door = door_dir
    return {
        "target_room": room_name,
        "final_door": door_dir,
        "path": path,
        "special_item": special_item,
        "explanation": explanation
    }


def parse_purchase_response(response: str):
    """Parse the purchase response from the LLM"""
    data = _parse_json_response(response)
    item = data.get("item", "").strip().upper()
    quantity = data.get("quantity", 0)
    explanation = data.get("explanation", "").strip()
    return {
        "item": item,
        "quantity": quantity,
        "explanation": explanation
    }


def parse_drafting_response(response: str):
    """Parse the drafting response from the LLM"""
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


def parse_parlor_response(response: str):
    """Parse the parlor puzzle response from the LLM"""
    data = _parse_json_response(response)
    box = data.get("box", "").strip().upper()
    explanation = data.get("explanation", "").strip()
    return {
        "box": box,
        "explanation": explanation
    }


def parse_terminal_response(response: str):
    """Parse the terminal response from the LLM"""
    data = _parse_json_response(response)
    command = data.get("command", "").strip()
    explanation = data.get("explanation", "").strip()
    return {
        "command": command,
        "explanation": explanation
    }


def parse_security_level_response(response: str):
    """Parse the security level response from the LLM"""
    data = _parse_json_response(response)
    security_level = data.get("security_level", "").strip()
    explanation = data.get("explanation", "").strip()
    return {
        "security_level": security_level,
        "explanation": explanation
    }


def parse_mode_response(response: str):
    """Parse the mode response from the LLM"""
    data = _parse_json_response(response)
    mode = data.get("mode", "").strip()
    explanation = data.get("explanation", "").strip()

    return {
        "mode": mode,
        "explanation": explanation
    }


def parse_lab_experiment_response(response: str):
    """Parse the lab experiment response from the LLM"""
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


def parse_coat_check_response(response: str):
    """Parse the coat check response from the LLM"""
    data = _parse_json_response(response)
    item = data.get("item", "").strip()
    explanation = data.get("explanation", "").strip()
    return {
        "item": item,
        "explanation": explanation
    }


def parse_secret_passage_response(response: str):
    """Parse the secret passage response from the LLM"""
    data = _parse_json_response(response)
    room_type = data.get("room_type", "").strip().upper()
    explanation = data.get("explanation", "").strip()
    return {
        "room_type": room_type,
        "explanation": explanation
    }


def parse_note_title_response(response: str):
    """Parse the note title response from the LLM"""
    data = _parse_json_response(response)
    title = data.get("title", "").strip()
    return title 