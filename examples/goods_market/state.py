import statistics
from typing import Any

from pydantic import Field, computed_field

from econagents.core.state.fields import EventField
from econagents.core.state.game import EventHandler, GameState, MetaInformation, PrivateInformation, PublicInformation


class GMMeta(MetaInformation):
    game_id: str = EventField(default="", exclude_from_mapping=True)
    player_number: int = EventField(default=0, exclude_from_mapping=True)
    round: int = EventField(default=0)
    # phase is inherited from MetaInformation and auto-updated by phase_transition events


class GMPrivate(PrivateInformation):
    # Updated via custom handler from wallet:wallet-update
    cash: float = EventField(default=10_000.0, exclude_from_mapping=True)
    shares: int = EventField(default=5, exclude_from_mapping=True)
    # Fetched from REST /state at market start; None if the game instance has no signals
    private_signal: float | None = EventField(default=None, exclude_from_mapping=True)


class GMPublic(PublicInformation):
    # Updated via custom handlers from dam:* events
    orders: dict[int, dict[str, Any]] = EventField(default_factory=dict, exclude_from_mapping=True)
    recent_prices: list[float] = EventField(default_factory=list, exclude_from_mapping=True)
    # Fetched from REST /state at market start; None if the game instance has no signals
    public_signal: float | None = EventField(default=None, exclude_from_mapping=True)

    @computed_field
    def current_share_value(self) -> float:
        tail = self.recent_prices[-7:]
        return statistics.median(tail) if tail else 0.0


class GMGameState(GameState):
    meta: GMMeta = Field(default_factory=GMMeta)
    private_information: GMPrivate = Field(default_factory=GMPrivate)
    public_information: GMPublic = Field(default_factory=GMPublic)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.meta.game_id = kwargs.get("game_id", "")
        self.meta.player_number = kwargs.get("player_number", 0)

    def get_custom_handlers(self) -> dict[str, EventHandler]:
        return {
            "dam:add-order": self._handle_dam_event,
            "dam:update-order": self._handle_dam_event,
            "dam:delete-order": self._handle_dam_event,
            "dam:contract-fulfilled": self._handle_contract_fulfilled,
            "wallet:wallet-update": self._handle_wallet_update,
        }

    def _handle_dam_event(self, event_type: str, data: dict[str, Any]) -> None:
        if event_type == "dam:add-order":
            order = data["order"]
            self.public_information.orders[order["id"]] = order
        elif event_type == "dam:update-order":
            order = data["order"]
            self.public_information.orders[order["id"]] = order
        elif event_type == "dam:delete-order":
            order_id = data["order"]["id"]
            self.public_information.orders.pop(order_id, None)

    def _handle_contract_fulfilled(self, event_type: str, data: dict[str, Any]) -> None:
        self.public_information.recent_prices.append(data["price"])

    def _handle_wallet_update(self, event_type: str, data: dict[str, Any]) -> None:
        for holding in data.get("holdings", []):
            if holding["asset"] == "cash":
                self.private_information.cash = holding["quantity"]
            elif holding["asset"] == "shares":
                self.private_information.shares = holding["quantity"]
