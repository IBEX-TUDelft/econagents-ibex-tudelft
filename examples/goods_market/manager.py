import asyncio
import json
from pathlib import Path
from typing import Any, Optional

import requests

from econagents.core.events import Message
from econagents.core.manager.phase import HybridPhaseManager
from econagents.core.transport import AuthenticationMechanism

from examples.create_game import API_BASE_URL
from examples.goods_market.roles import Trader
from examples.goods_market.state import GMGameState


class GoodsMarketAuth(AuthenticationMechanism):
    """
    Sends the game-engine WebSocket join message:
      {"meta": {"type": "join", "gameId": <id>}, "payload": {"recovery": <token>}}
    """

    async def authenticate(self, transport, **kwargs) -> bool:
        msg = {
            "meta": {"type": "join", "gameId": kwargs["game_id"]},
            "payload": {"recovery": kwargs["token"]},
        }
        await transport.send(json.dumps(msg))
        return True


class GoodsMarketManager(HybridPhaseManager):
    def __init__(self, game_id: str, player_number: int, token: str, personality: Optional[str] = None):
        super().__init__(
            state=GMGameState(game_id=game_id, player_number=player_number),
            agent_role=Trader(personality=personality),
            auth_mechanism=GoodsMarketAuth(),
            auth_mechanism_kwargs={"game_id": game_id, "token": token},
            phase_transition_event="phase_transition:phase-transition",
            phase_identifier_key="phase",
            continuous_phases={1},
            min_action_delay=20,
            max_action_delay=40,
            prompts_dir=Path(__file__).parent / "prompts",
        )
        self.game_id = game_id
        self.player_number = player_number
        self._token = token
        self.register_event_handler("join:player-joined", self._handle_player_joined)

    def _extract_message_data(self, raw_message: str) -> Optional[Message]:
        """Remap the game-engine wire format to what econagents expects.

        Game engine sends: {"type": <event>, "payload": {...}}
        econagents expects: Message(event_type=<event>, data={...})
        """
        try:
            msg = json.loads(raw_message)
            event_type = msg.get("type", "")
            data = msg.get("payload", {})
        except json.JSONDecodeError:
            self.logger.error("Received invalid JSON.")
            return None
        return Message(message_type="event", event_type=event_type, data=data)

    async def handle_phase_transition(self, new_phase: Optional[int]) -> None:
        """Fetch signals from the REST state endpoint when the market phase begins."""
        if new_phase == 1:
            await asyncio.to_thread(self._fetch_signals)
        await super().handle_phase_transition(new_phase)

    def _fetch_signals(self) -> None:
        """Synchronous REST call — run via asyncio.to_thread to avoid blocking the event loop."""
        try:
            url = f"{API_BASE_URL}/games/{self.game_id}/state"
            resp = requests.get(url, params={"recovery": self._token}, timeout=5)
            resp.raise_for_status()
            dam = resp.json().get("components", {}).get("dam", {})

            public_signal = dam.get("publicSignal")
            self.state.public_information.public_signal = float(public_signal) if public_signal is not None else None

            for entry in dam.get("privateSignals", []):
                if entry.get("playerNumber") == self.player_number:
                    self.state.private_information.private_signal = float(entry["value"])
                    break

            self.logger.info(
                f"Signals fetched — public={self.state.public_information.public_signal}, "
                f"private={self.state.private_information.private_signal}"
            )
        except Exception as e:
            self.logger.warning(f"Could not fetch signals: {e}")

    async def _handle_player_joined(self, message: Message) -> None:
        """Send player-is-ready when the server confirms our own join (phase 0 only)."""
        if message.data.get("playerNumber") == self.player_number:
            ready_msg = {
                "meta": {"type": "player-is-ready", "gameId": self.game_id},
                "payload": {},
            }
            await self.send_message(json.dumps(ready_msg))
            self.logger.info("Sent player-is-ready")
