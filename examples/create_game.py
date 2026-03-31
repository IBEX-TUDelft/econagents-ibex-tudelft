import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()

HOSTNAME = os.getenv("HOSTNAME", "localhost")
API_PORT = os.getenv("API_PORT", "3089")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def join_game(game_id: str, player_number: int | None = None) -> dict[str, Any]:
    """
    Claim a player slot in a running game via the game engine REST API.

    Sends POST /games/{game_id}/join and returns the token and player metadata
    needed to open a WebSocket connection. Reads HOSTNAME and API_PORT from
    the environment.

    Args:
        game_id: ID of the running game to join.
        player_number: Optional specific slot to request.

    Returns:
        Dict with keys: token, playerNumber, role, tag.
    """
    url = f"http://{HOSTNAME}:{API_PORT}/games/{game_id}/join"
    body: dict[str, Any] = {}
    if player_number is not None:
        body["playerNumber"] = player_number

    logger.info(f"Joining game {game_id} at {url}")
    response = requests.post(url, json=body, headers={"Content-Type": "application/json"}, timeout=10)
    response.raise_for_status()

    data = response.json()
    logger.info(f"Joined as player {data['playerNumber']} (role={data['role']}, tag={data.get('tag')})")
    return data


def calculate_total_agents(game_params: dict[str, Any]) -> int:
    """Calculate total number of agents from game parameters."""
    return (
        game_params.get("speculators", {}).get("count", 0)
        + game_params.get("developers", {}).get("count", 0)
        + game_params.get("owners", {}).get("count", 0)
    )


def load_game_specs(specs_path: Path) -> dict[str, Any]:
    """Load game specifications from JSON file."""
    try:
        with specs_path.open("r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load game specs: {e}")
        raise


def create_game(base_url: str, username: str, password: str, game_params: dict[str, Any]) -> dict[str, Any]:
    """Create a new game using the API."""
    endpoint = f"{base_url}/api/v1/games/create-for-llm"

    payload = {"username": username, "password": password, "gameParameters": game_params}
    logger.info(f"Creating game with payload: {payload}")

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create game: {e}")
        raise


def get_recovery_code(base_url: str, game_id: int) -> str:
    """Get a recovery code for a player in the game."""
    endpoint = f"{base_url}/api/v1/games/get-recovery"

    try:
        response = requests.get(f"{endpoint}?game_id={game_id}", timeout=30)
        response.raise_for_status()
        return response.json()["data"]["recovery"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get recovery code: {e}, response: {response.json()}")
        raise


def save_game_data(specs_path: Path, game_id: int, game_name: str, num_agents: int, recovery_codes: list[str]) -> None:
    """Save game data to a JSON file in the specs/games directory."""
    specs_dir = specs_path.parent / "games"
    specs_dir.mkdir(parents=True, exist_ok=True)

    game_data = {"game_id": game_id, "agents": num_agents, "game_name": game_name, "recovery_codes": recovery_codes}

    output_file = specs_dir / f"game_{game_id}.json"
    try:
        with output_file.open("w") as f:
            json.dump(game_data, f, indent=4)
        logger.info(f"Game data saved to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save game data: {e}")
        raise


def create_game_from_specs(
    specs_path: Path, base_url: str, game_name: str, credentials: dict[str, Any]
) -> dict[str, Any]:
    """
    Create a new game from specs and return game ID and login payloads.

    Args:
        specs_path: Path to game specification file
        base_url: Base URL of the game server
        game_name: Name for the game

    Returns:
        Dictionary containing game_id, num_agents, and login_payloads
    """
    username = credentials["username"]
    password = credentials["password"]

    if not username or not password:
        logger.error("Missing credentials. Please set GAME_USERNAME and GAME_PASSWORD environment variables.")
        raise ValueError("Missing credentials")

    try:
        game_params = load_game_specs(specs_path)
        game_params["title"] = game_name

        # Calculate total number of agents from game parameters
        num_agents = calculate_total_agents(game_params)
        logger.info(f"Total number of agents: {num_agents}")

        logger.info("Creating new game...")
        result = create_game(base_url, username, password, game_params)

        if result.get("status"):
            game_id = result["data"]["id"]
            logger.info(f"Game created successfully! Game ID: {game_id}")

            # Get recovery codes for all agents
            logger.info("Getting recovery codes for all agents...")
            recovery_codes = [get_recovery_code(base_url, game_id) for _ in range(num_agents)]

            # Create login payloads for each agent
            login_payloads = []
            for recovery_code in recovery_codes:
                login_payloads.append(
                    {
                        "gameId": game_id,
                        "type": "join",
                        "recovery": recovery_code,
                    }
                )

            return {"game_id": game_id, "num_agents": num_agents, "login_payloads": login_payloads}
        else:
            error_msg = result.get("message", "Unknown error")
            logger.error(f"Failed to create game: {error_msg}")
            raise ValueError(f"Failed to create game: {error_msg}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise


if __name__ == "__main__":
    GAME_SERVER_URL = f"http://{HOSTNAME}"
    SPECS_PATH = Path(__file__).parent / "specs/example/harberger.json"  # Updated default path
    GAME_NAME = f"harberger {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    USERNAME = os.getenv("GAME_USERNAME")
    PASSWORD = os.getenv("GAME_PASSWORD")

    if not SPECS_PATH.exists():
        logger.error(f"Game specs file not found at {SPECS_PATH}")
        exit(1)

    create_game_from_specs(
        specs_path=SPECS_PATH,
        base_url=GAME_SERVER_URL,
        game_name=GAME_NAME,
        credentials={"username": USERNAME, "password": PASSWORD},
    )
