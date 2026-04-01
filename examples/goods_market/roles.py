import json
import time
from typing import Any, Optional

from econagents.llm.openai import ChatOpenAI
from econagents_ibex_tudelft import PersonaAgentRole


class Trader(PersonaAgentRole):
    role = 1
    name = "Trader"
    llm = ChatOpenAI()
    task_phases = [1]  # Only act during the market phase

    def parse_phase_1_llm_response(self, response: str, state: Any) -> Optional[dict]:
        """
        Parse the LLM's market-phase output and wrap it in the game engine wire format.

        The LLM is expected to return one of:
          {"action": "post-order", "type": "bid"|"ask", "price": <int>, "now": <bool>}
          {"action": "cancel-order", "order_id": <int>}
          {"action": "none"}

        Returns None for "none" (no message sent) or on parse failure.
        """
        try:
            action = json.loads(response)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse LLM response as JSON: {response!r}")
            return None

        game_id = state.meta.game_id
        player_number = state.meta.player_number

        if action.get("action") == "post-order":
            return {
                "meta": {"type": "post-order", "gameId": game_id},
                "payload": {
                    "sender": player_number,
                    "type": action["type"],
                    "price": int(action["price"]),
                    "timestamp": int(time.time() * 1000),
                    "now": bool(action.get("now", False)),
                },
            }

        if action.get("action") == "cancel-order":
            return {
                "meta": {"type": "cancel-order", "gameId": game_id},
                "payload": {
                    "sender": player_number,
                    "orderId": action["order_id"],
                },
            }

        return None  # "none" action → nothing is sent
