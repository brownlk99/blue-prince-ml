# Blue Prince ML

Blue Prince ML is an AI agent built to play the game "Blue Prince." It uses a Large Language Model (LLM) to make decisions, navigate the game world, solve puzzles, and manage resources, with the goal of reaching the Antechamber.

## Features

- **LLM-Powered Decision Making:** Uses a configurable Large Language Model (e.g., o4-mini, sonnet-4, gemini-2.5-pro) to determine the course of action based on the current game state.
- **Game State Management:** Tracks game progress, including the house map, rooms, player resources, items, notes, and additional "learned" pieces of information.
- **Persistent Memory:** Saves and loads game states, allowing for sessions to be continued. It also maintains memory of past decisions, explored rooms, and game terminology across runs.
- **Screen Capture and OCR:** Leverages automation from the use of `easyocr` and `google-cloud-vision` to read text and gather information from the game's user interface.
- **Interactive CLI:** A command-line interface allows the user to initiate interactions between the game and the LLM.
- **Modular Architecture:** The project is organized into distinct modules for game logic, the LLM agent, CLI, and capture utilities, making it easier to extend and maintain.

## How It Works: The Gameplay Loop

The application's core is a multi-step loop driven by the command-line interface, which facilitates interaction between the player (you), the AI agent, and the game. The standard operational flow is managed by the `CommandHandler` in `cli/command_handler.py`, with available actions listed in `cli/menu.py`.

1.  **Resource and Room Capture:** The loop begins when the user initiates an action. The first step is to synchronize the `GameState` with the game client.
    *   **OCR Capture:** The system automatically triggers an OCR capture of the game screen to read the player's current resources (keys, gems, coins, etc.).
    *   **Error Correction:** If the OCR successfully reads a number, the user is asked to confirm it. If there's an error, the user can manually correct the value. If the OCR fails to identify a number, it saves an image of the number to the `capture/number_templates/` directory and prompts the user to identify it. This renames the file, training the OCR for future recognition.

2.  **LLM Action Query:** With an up-to-date `GameState`, the system queries the LLM for its next move. The `ActionHandler` compiles the current game context, including resources, room layout, and past decisions, into a prompt for the `BluePrinceAgent`.

3.  **LLM Decision and Action Execution:** The LLM returns a JSON object specifying which action to take. The `ActionHandler` then executes the corresponding logic. The primary actions are detailed below.

4.  **State Persistence:** After each significant action, the `GameState` and agent memories are automatically saved to JSON files, ensuring that all progress and learned information are preserved between sessions.

### Player Commands (The Bridge)

The `CommandHandler` acts as the bridge between the player and the AI. It provides a set of commands that the player can execute from the CLI menu. These commands are the primary way to manage the game state, gather information, and trigger LLM actions.

-   **`capture_resources`**: Manually triggers the OCR to read the player's resources from the screen and update the `GameState`.
-   **`capture_note`**: Captures a note from the game screen using OCR. It then asks the LLM to generate a concise title for the note before saving it to memory.
-   **`capture_items`**: Uses OCR to capture a special item's name and description from the screen, adding it to the inventory.
-   **`stock_shelves`**: Specifically for `ShopRoom`s, this command uses OCR to read the items available for sale and their prices.
-   **`take_action`**: This is the main command to query the LLM. It captures resources first, then asks the LLM to decide on the next high-level action to take.
-   **`drafting_options`**: After the LLM has decided to `open_door`, and the player has revealed the drafting screen in-game, this command captures the three room choices via OCR and prompts the LLM to select one.
-   **`add_term_to_memory`**: Allows the player to manually add a term and its definition to the agent's long-term memory.
-   **`set_dig_spots` / `set_trunks`**: Lets the player manually set the number of dig spots or trunks in a room.
-   **`edit_doors`**: Opens the interactive Door Editor for the current room, allowing the player to add, remove, or modify doors.
-   **`edit_items_for_sale`**: Opens an editor to manually change the items and prices in a `ShopRoom`.
-   **`fill_room_attributes`**: A utility to automatically populate the attributes of a newly discovered room based on its name.
-   **`manual_llm_follow_up`**: Allows the player to ask the LLM for a more detailed explanation of its most recent decision.
-   **`show_house_map`**: Displays a text-based map of the current house layout in the terminal.
-   **`call_it_a_day`**: Ends the current run and saves the final game state.

### LLM Actions

The LLM can choose from a variety of actions, each with a specific purpose in the gameplay loop:

-   **`move`**: The LLM specifies a `target_room` it wants to reach and a `planned_action` it intends to perform there. This plan is saved to the agent's memory and included in the next prompt to help the LLM "remember" its goal.
-   **`open_door`**: The LLM chooses a door (N, S, E, W) in the current room to open. This is the first step in discovering a new room.
    *   **Player Action:** The player must manually go to the specified door in the game to reveal the "Drafting Options" screen.
    *   **Drafting:** The player then runs the `drafting_options` command. OCR scans the three room choices, and the LLM is prompted to select one and decide whether to `enter`.
    *   **Entering a New Room:** If the LLM chooses to enter, the player moves into the new room. The CLI then launches a **Door Editor**. The player must update the information for the new room's doors (e.g., marking them as security doors). A shortcut is available (`option 4`) to mark all doors as not being security doors. The player is responsible for manually collecting any items or resources in the new room.
-   **`peruse_shop`**: Stocks the inventory of the current `ShopRoom` by using OCR to read the items for sale on the screen.
-   **`purchase_item`**: The LLM decides which item to buy from a shop.
-   **`solve_puzzle`**: Initiates the process for solving a `PuzzleRoom`, typically the parlor puzzle, using OCR to read the clues.
-   **`open_secret_passage`**: The LLM decides which type of room to access via a `SecretPassage`.
-   **`dig` / `open_trunk`**: The player manually informs the system how many dig spots or trunks are in the room.
-   **`use_terminal`**: The LLM chooses a command to execute on a terminal in rooms like the `Security`, `Office`, or `Laboratory`.
-   **`store_item_in_coat_check` / `retrieve_item_in_coat_check`**: The LLM decides which item to store or retrieve from the `CoatCheck` room, allowing items to persist between runs.
-   **`toggle_*_switch`**: Flips a specific switch in the `UtilityCloset`.
-   **`call_it_a_day`**: Ends the current session, saves all progress, and stores relevant information for the next run.

## Core Modules

-   **`main.py`**: The entry point of the application. It handles argument parsing, initializes all core components, and starts the CLI menu.
-   **`/game`**: Contains the core game logic, including classes for the `GameState`, `HouseMap`, `Room`, and other game-specific elements.
-   **`/llm`**: Home to the `BluePrinceAgent`, which is the brain of the operation. It manages communication with the LLM, formats prompts, and interprets responses.
-   **`/cli`**: Implements the user-facing command-line interface, handling user input and orchestrating the agent's actions.
-   **`/capture`**: Provides utilities for screen capture and Optical Character Recognition (OCR), enabling the agent to "see" the game.
-   **`/jsons`**: Stores persistent data, including saved games (`current_run.json`), and the agent's long-term memory files.

## Setup and Configuration

Before running the application, you need to set up your environment and configure the necessary API keys.

### 1. Virtual Environment

It is highly recommended to use a Python virtual environment to manage dependencies. Create and activate a new environment:

```bash
# Create a new virtual environment (e.g., named 'venv')
python -m venv venv

# Activate the environment
# On Windows
.\venv\Scripts\activate

# On macOS and Linux
source venv/bin/activate
```

### 2. Install Dependencies

Install the required Python packages.

```bash
pip install -r requirements.txt
```

Alternatively, you can install the packages individually.

### 3. API Key Configuration

The application requires API keys for both Google Cloud Vision and the LLM providers you intend to use. You are responsible for managing your own API keys and ensuring they are set up correctly.

#### Google Cloud Vision

To use Google Cloud Vision for OCR, you need to set up a Google Cloud project, enable the API, and configure authentication.

1.  **Create or Select a Google Cloud Project:**
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project or select an existing one.

2.  **Enable the Cloud Vision API:**
    *   In the Cloud Console, navigate to the **APIs & Services > Library**.
    *   Search for "Cloud Vision API" and enable it for your project.
    *   Alternatively, you can enable it using the `gcloud` command-line tool:
        ```bash
gcloud services enable vision.googleapis.com
        ```

3.  **Enable Billing:**
    *   The Vision API requires billing to be enabled. You can set this up in the **Billing** section of the Cloud Console.
    *   You can also link your project to a billing account using `gcloud`:
        ```bash
gcloud billing projects link YOUR_PROJECT_ID --billing-account=YOUR_BILLING_ACCOUNT_ID
        ```

4.  **Set Up Authentication:**
    The application uses Application Default Credentials (ADC) to find your credentials automatically. You have two primary options:

    *   **Option A: Authenticate with the Google Cloud SDK**
        1.  [Install and initialize the Google Cloud SDK](https://cloud.google.com/sdk/docs/install).
        2.  Run the following command to log in and set your application-default credentials:
            ```bash
gcloud auth application-default login
            ```
        The client library will automatically detect these credentials.

    *   **Option B: Use a Service Account Key File**
        1.  Follow the official Google Cloud documentation to [create a service account and download a JSON key file](https://cloud.google.com/vision/docs/setup).
        2.  Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the absolute path of your JSON key file. For example:

            ```bash
# On Windows (Command Prompt)
set GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\keyfile.json"

# On Windows (PowerShell)
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\keyfile.json"

# On macOS and Linux
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/keyfile.json"
            ```

#### LLM Providers

You need to install the client library for each LLM provider you want to use and set the corresponding API key as an environment variable.

-   **OpenAI:**
    ```bash
pip install openai
# Set your API key
export OPENAI_API_KEY="your-openai-api-key"
    ```

-   **Anthropic (Claude):**
    ```bash
pip install anthropic
# Set your API key
export ANTHROPIC_API_KEY="your-anthropic-api-key"
    ```

-   **Google (Gemini):
    ```bash
pip install google-genai google-generativeai
# Set your API key
export GEMINI_API_KEY="your-google-api-key"
    ```

    **Note:** The application checks for `GEMINI_API_KEY` first. If it is not found, it will check for `GOOGLE_API_KEY` as a legacy option.

#### Google (Gemini) API

If you plan to use Google Gemini models, you also need to ensure the Generative Language API is enabled in your Google Cloud project.

1.  **Enable the Generative Language API:**
    *   In the Cloud Console, navigate to the **APIs & Services > Library**.
    *   Search for "Generative Language API" and enable it for your project.
    *   Alternatively, you can enable it using the `gcloud` command-line tool:
        ```bash
gcloud services enable generativelanguage.googleapis.com
        ```

---

**Important Note:** The information provided in this `README.md` regarding Google Cloud setup is accurate as of July 6, 2025. Google Cloud services and their setup procedures are subject to change. Always refer to the [official Google Cloud documentation](https://cloud.google.com/docs) for the most up-to-date and accurate instructions before performing any actions.

## Usage

To run the Blue Prince ML agent, use the command line from the root directory.

### Arguments

-   `--day` or `-d` (required): The current day/run number for the session.
-   `--load` or `-l` (optional): Path to a saved game state JSON file to load.
-   `--model` or `-m` (optional): The LLM model to use (e.g., `openai:o4-mini`). Defaults to `o4-mini`.
-   `--use_utility_model` or `-u` (optional): Use a smaller, faster utility model for simple tasks.
-   `--verbose` or `-v` (optional): If set, the full prompts sent to the LLM will be displayed.
-   `--editor` or `-e` (optional): Path to a text editor for certain interactive tasks. If not provided, the application will attempt to use the `EDITOR_PATH` environment variable. For example, to use VS Code as your editor, you can set `EDITOR_PATH="code"` (or the full path to `code.exe` on Windows).

### Example Commands

**Start a new game on day 1:**

```bash
python main.py --day 1
```

**Load a game from a save file:**

```bash
python main.py --day 5 --load ./jsons/current_run.json
```

**Run in verbose mode with a specific model:**

```bash
python main.py --day 3 --verbose --model openai:gpt-4
```

## Dependencies

The project relies on several key Python libraries, which should be installed via a requirements file or a virtual environment.

### Core Libraries

-   **`easyocr`**: For Optical Character Recognition (OCR) to extract text from images.
-   **`google-cloud-vision`**: Used for more advanced OCR and image analysis capabilities.
-   **`opencv-python` (`cv2`)**: For image processing tasks, such as preparing screenshots for OCR.
-   **`numpy`**: A fundamental package for scientific computing, used for handling image data.
-   **`Pillow` (`PIL`)**: For capturing and manipulating images.

### LLM and NLP

-   **`openai`**: The official client library for interacting with OpenAI models like GPT-4.
-   **`anthropic`**: Client library for Anthropic's language models (e.g., Claude).
-   **`google-generativeai`**: Google's client library for their generative AI models.
-   **`tiktoken`**: Used for token counting to manage context windows for OpenAI models.
-   **`textblob`**: Provides a simple API for common NLP tasks like text correction.

### Standard Libraries

The project also makes extensive use of Python's standard libraries, including:

-   `argparse`: For parsing command-line arguments.
-   `json`: For serializing and deserializing game data and memory files.
-   `os`: For interacting with the operating system, such as file paths.
-   `time`: For handling delays and timing-related functions.
-   `typing`: For type hints to improve code clarity and maintainability.
-   `warnings`: For managing warning messages.
-   `contextlib`: For managing resources with context managers.
-   `threading`: For running tasks in parallel, such as animations.
-   `difflib`: For comparing text sequences.
-   `hashlib`: For generating hash values.
-   `itertools`: For creating efficient iterators.
-   `sys`: For system-specific parameters and functions.
-   `traceback`: For formatting and printing stack traces.
-   `functools`: For higher-order functions and operations on callable objects.
