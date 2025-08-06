from typing import Any, Dict, List, Optional

from econagents.core.state.fields import EventField
from econagents.core.state.game import (
    EventHandler,
    GameState,
    MetaInformation,
    PrivateInformation,
    PublicInformation,
)
from econagents.core.state.market import MarketState
from pydantic import BaseModel, Field, computed_field

from econagents_ibex_tudelft import ChatState

# EventField lets you specify the event key of the event data in the message
# event_key is the key of the event data in the message. If not specified, the event key is the field name.
# exclude_from_mapping is used to exclude the field from the mapping of the event data, so it is not updated when an event is processed
# exclude_events is used to exclude the field from the events that trigger an update, so it is not updated when an event is processed
# events are the events that trigger an update, if not specified, all events will trigger an update if they have the event key


class CompensationRequest(BaseModel):
    number: int
    compensation: Optional[int] = None


class VMeta(MetaInformation):
    # These fields are required in MetaInformation
    game_id: int = EventField(default=0, exclude_from_mapping=True)
    player_name: Optional[str] = EventField(default=None, event_key="name")
    player_number: Optional[int] = EventField(default=None, event_key="number")
    players: list[dict[str, Any]] = EventField(default_factory=list, event_key="players")
    phase: int = EventField(default=0, event_key="phase")


class VPrivate(PrivateInformation):
    # PrivateInformation can have have any fields
    wallet: list[dict[str, Any]] = EventField(default_factory=list)
    value_signals: list[float] = EventField(default_factory=list, event_key="signals")
    declarations: list[dict[str, Any]] = EventField(default_factory=list)
    property: dict[str, Any] = EventField(default_factory=dict, exclude_events=["profit"])

    # Store the raw event data for compensation requests.
    raw_compensation: Dict[str, Any] = EventField(default_factory=dict, event_key="compensation-requests-received")

    @computed_field
    def compensationRequestsReceived(self) -> List[CompensationRequest]:
        """Process and sort the raw compensation requests from smallest to largest amount."""
        raw_data = self.raw_compensation or {}
        requests = []

        # Extract and create CompensationRequest objects
        for item in raw_data.get("compensationRequests", []):
            comp_value = None
            if "compensationRequests" in item and len(item.get("compensationRequests", [])) > 1:
                comp_value = item["compensationRequests"][1]  # Get the second element (actual compensation value)
            requests.append(CompensationRequest(number=item["number"], compensation=comp_value))

        # Sort requests by compensation amount
        # Handle None values by putting them at the start
        return sorted(
            requests,
            key=lambda x: float("inf") if x.compensation is None else x.compensation,
        )


class VPublic(PublicInformation):
    # PublicInformation can have any fields
    # Tax
    tax_rate: float = EventField(default=0, event_key="taxRate")
    initial_tax_rate: float = EventField(default=0, event_key="initialTaxRate")
    final_tax_rate: float = EventField(default=0, event_key="finalTaxRate")

    # Boundaries and conditions
    boundaries: dict[str, Any] = EventField(default_factory=dict)
    conditions: list[dict[str, Any]] = EventField(default_factory=list)

    # Market
    value_signals: list[float] = EventField(default_factory=list, event_key="signals")
    market_state: MarketState = EventField(default_factory=MarketState)
    public_signal: list[float] = EventField(default_factory=list, event_key="publicSignal")

    # chat box
    chat_state: ChatState = EventField(default_factory=ChatState)

    # compensation offer
    # Event structure: {"type":"event","eventType":"compensation-offer-made","data":{"compensationOffers":[null,300000]}}
    compensationOffers: list[Optional[float]] = EventField(
        default_factory=lambda: [None, None], event_key="compensationOffers"
    )

    # Winning condition
    winning_condition: int = EventField(default=0, event_key="winningCondition")

    @computed_field
    def winning_condition_description(self) -> dict[str, Any]:
        return self.conditions[self.winning_condition] if self.conditions else {}


class VGameState(GameState):
    meta: VMeta = Field(default_factory=VMeta)
    private_information: VPrivate = Field(default_factory=VPrivate)
    public_information: VPublic = Field(default_factory=VPublic)

    # This is needed because the game_id is not in the event data
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.meta.game_id = kwargs.get("game_id", 0)

    # This is needed to build the order book
    def get_custom_handlers(self) -> dict[str, EventHandler]:
        """Provide custom event handlers for market, chat, and compensation events"""
        market_events = [
            "add-order",
            "update-order",
            "delete-order",
            "contract-fulfilled",
            "asset-movement",
        ]

        handlers = {event: self._handle_market_event for event in market_events}
        handlers["message-received"] = self._handle_chat_event

        return handlers

    # This is needed to build the order book
    def _handle_market_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Handle market-related events by delegating to MarketState"""
        self.public_information.market_state.process_event(event_type=event_type, data=data)

        if event_type == "asset-movement":
            winning_condition = self.public_information.winning_condition
            self.private_information.wallet[winning_condition]["balance"] = data["balance"]
            self.private_information.wallet[winning_condition]["shares"] = data["shares"]

    # This is needed to build the chat log
    def _handle_chat_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Handle chat-related events by delegating to ChatState"""
        self.public_information.chat_state.process_event(event_type=event_type, data=data)
