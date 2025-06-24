# import json
# import os


# def update_json(filepath: str, incoming_data: dict):
#     try:
#         if os.path.exists(filepath):
#             with open(filepath, 'r') as file:
#                 current_data = json.load(file)
#         else:
#             current_data = {}
#     except (json.JSONDecodeError, OSError) as e:
#         print(f"Warning: Failed to load existing JSON from {filepath}. Reason: {e}")
#         current_data = {}

#     for group_key, subdict in incoming_data.items():
#         if not isinstance(subdict, dict):
#             print(f"Warning: Expected dict for group '{group_key}', got {type(subdict)}")
#             continue

#         if group_key not in current_data:
#             current_data[group_key] = {}

#         # Update the sub-dictionary
#         current_data[group_key].update(subdict)

#     with open(filepath, 'w') as file:
#         serializable_data = make_json_serializable(current_data)
#         json.dump(serializable_data, file, indent=4)

# def append_to_list_json(filepath: str, new_entries: list[dict]):
#     try:
#         if os.path.exists(filepath):
#             with open(filepath, 'r') as file:
#                 current_data = json.load(file)
#                 if not isinstance(current_data, list):
#                     print(f"Warning: Expected a list in {filepath}, got {type(current_data)}. Overwriting.")
#                     current_data = []
#         else:
#             current_data = []
#     except (json.JSONDecodeError, OSError) as e:
#         print(f"Warning: Failed to load JSON from {filepath}. Reason: {e}")
#         current_data = []

#     # Append new entries
#     current_data.extend(new_entries)

#     with open(filepath, 'w') as file:
#         json.dump(current_data, file, indent=4)

# def make_json_serializable(obj):
#     if isinstance(obj, list):
#         return [make_json_serializable(x) for x in obj]
#     elif isinstance(obj, dict):
#         return {k: make_json_serializable(v) for k, v in obj.items()}
#     elif hasattr(obj, 'to_dict'):
#         return make_json_serializable(obj.to_dict())
#     else:
#         return obj
    
# #not used
# def summarize_game_state() -> str:
#     with open("current_run.json", "r") as f:
#         state = json.load(f)
#     summary = []

#     # Resources
#     res = state["resources"]
#     summary.append(f"Resources: footprints={res['footprints']}, gems={res['gems']}, dice={res['dice']}, keys={res['keys']}, coins={res['coins']}")

#     # Current position
#     pos = state["current_position"]
#     summary.append(f"Current room position: ({pos['x']}, {pos['y']})")

#     # Discovered rooms
#     summary.append("Discovered rooms:")
#     for y, row in enumerate(state["house"]["rooms"]):
#         for x, room in enumerate(row):
#             if room:
#                 doors = ", ".join([f"{k} (discovered={v['discovered']}, locked={v['locked']})" for k, v in room["doors"].items()])
#                 summary.append(f" - {room['name']} at ({x}, {y}), doors: {doors}")

#     return "\n".join(summary)