import pytest

from econagents_ibex_tudelft.core.state.market import MarketState, Order, Trade


class TestOrder:
    def test_order_creation(self):
        """Test creating an Order object"""
        order = Order(
            id=1,
            sender=100,
            price=50.0,
            quantity=10.0,
            type="bid",
            condition=1,
            now=False,
        )

        assert order.id == 1
        assert order.sender == 100
        assert order.price == 50.0
        assert order.quantity == 10.0
        assert order.type == "bid"
        assert order.condition == 1
        assert order.now is False

    def test_order_defaults(self):
        """Test Order with default 'now' field"""
        order = Order(
            id=2,
            sender=200,
            price=55.0,
            quantity=5.0,
            type="ask",
            condition=2,
        )

        assert order.now is False


class TestTrade:
    def test_trade_creation(self):
        """Test creating a Trade object"""
        trade = Trade(
            from_id=100,
            to_id=200,
            price=50.0,
            quantity=10.0,
            condition=1,
            median=49.5,
        )

        assert trade.from_id == 100
        assert trade.to_id == 200
        assert trade.price == 50.0
        assert trade.quantity == 10.0
        assert trade.condition == 1
        assert trade.median == 49.5

    def test_trade_optional_median(self):
        """Test Trade with optional median field"""
        trade = Trade(
            from_id=100,
            to_id=200,
            price=50.0,
            quantity=10.0,
            condition=1,
        )

        assert trade.median is None


class TestMarketState:
    @pytest.fixture
    def market_state(self):
        """Create a fresh MarketState for each test"""
        return MarketState()

    def test_initial_state(self, market_state):
        """Test that MarketState initializes with empty orders and trades"""
        assert market_state.orders == {}
        assert market_state.trades == []
        assert isinstance(market_state.orders, dict)
        assert isinstance(market_state.trades, list)

    def test_add_order(self, market_state):
        """Test adding an order to the market"""
        order_data = {
            "id": 1,
            "sender": 100,
            "price": 50.0,
            "quantity": 10.0,
            "type": "bid",
            "condition": 1,
            "now": False,
        }

        market_state.process_event("add-order", {"order": order_data})

        assert 1 in market_state.orders
        assert market_state.orders[1].price == 50.0
        assert market_state.orders[1].sender == 100
        assert market_state.orders[1].type == "bid"

    def test_add_multiple_orders(self, market_state):
        """Test adding multiple orders to the market"""
        orders = [
            {"id": 1, "sender": 100, "price": 50.0, "quantity": 10.0, "type": "bid", "condition": 1},
            {"id": 2, "sender": 200, "price": 55.0, "quantity": 5.0, "type": "ask", "condition": 1},
            {"id": 3, "sender": 300, "price": 48.0, "quantity": 8.0, "type": "bid", "condition": 1},
        ]

        for order_data in orders:
            market_state.process_event("add-order", {"order": order_data})

        assert len(market_state.orders) == 3
        assert market_state.orders[1].type == "bid"
        assert market_state.orders[2].type == "ask"
        assert market_state.orders[3].price == 48.0

    def test_update_order(self, market_state):
        """Test updating an existing order"""
        # First add an order
        order_data = {
            "id": 1,
            "sender": 100,
            "price": 50.0,
            "quantity": 10.0,
            "type": "bid",
            "condition": 1,
        }
        market_state.process_event("add-order", {"order": order_data})

        # Update the order quantity
        update_data = {"id": 1, "quantity": 5.0}
        market_state.process_event("update-order", {"order": update_data})

        assert market_state.orders[1].quantity == 5.0
        # Other fields should remain unchanged
        assert market_state.orders[1].price == 50.0
        assert market_state.orders[1].sender == 100

    def test_update_nonexistent_order(self, market_state):
        """Test updating a non-existent order (should be ignored)"""
        update_data = {"id": 999, "quantity": 5.0}
        market_state.process_event("update-order", {"order": update_data})

        assert 999 not in market_state.orders

    def test_delete_order(self, market_state):
        """Test deleting an order from the market"""
        # First add an order
        order_data = {
            "id": 1,
            "sender": 100,
            "price": 50.0,
            "quantity": 10.0,
            "type": "bid",
            "condition": 1,
        }
        market_state.process_event("add-order", {"order": order_data})
        assert 1 in market_state.orders

        # Delete the order
        market_state.process_event("delete-order", {"order": {"id": 1}})

        assert 1 not in market_state.orders

    def test_delete_nonexistent_order(self, market_state):
        """Test deleting a non-existent order (should be ignored)"""
        market_state.process_event("delete-order", {"order": {"id": 999}})
        # Should not raise any error

    def test_contract_fulfilled(self, market_state):
        """Test recording a trade when a contract is fulfilled"""
        trade_data = {
            "from": 100,
            "to": 200,
            "price": 50.0,
            "quantity": 10.0,
            "condition": 1,
            "median": 49.5,
        }

        market_state.process_event("contract-fulfilled", trade_data)

        assert len(market_state.trades) == 1
        assert market_state.trades[0].from_id == 100
        assert market_state.trades[0].to_id == 200
        assert market_state.trades[0].price == 50.0
        assert market_state.trades[0].median == 49.5

    def test_contract_fulfilled_without_quantity(self, market_state):
        """Test contract fulfilled with default quantity"""
        trade_data = {
            "from": 100,
            "to": 200,
            "price": 50.0,
            "condition": 1,
        }

        market_state.process_event("contract-fulfilled", trade_data)

        assert market_state.trades[0].quantity == 1.0

    def test_get_orders_from_player(self, market_state):
        """Test getting all orders from a specific player"""
        orders = [
            {"id": 1, "sender": 100, "price": 50.0, "quantity": 10.0, "type": "bid", "condition": 1},
            {"id": 2, "sender": 200, "price": 55.0, "quantity": 5.0, "type": "ask", "condition": 1},
            {"id": 3, "sender": 100, "price": 48.0, "quantity": 8.0, "type": "bid", "condition": 1},
            {"id": 4, "sender": 300, "price": 52.0, "quantity": 3.0, "type": "ask", "condition": 1},
        ]

        for order_data in orders:
            market_state.process_event("add-order", {"order": order_data})

        player_100_orders = market_state.get_orders_from_player(100)
        assert len(player_100_orders) == 2
        assert all(order.sender == 100 for order in player_100_orders)

        player_200_orders = market_state.get_orders_from_player(200)
        assert len(player_200_orders) == 1
        assert player_200_orders[0].id == 2

        # Non-existent player
        player_999_orders = market_state.get_orders_from_player(999)
        assert len(player_999_orders) == 0

    def test_order_book_computed_field(self, market_state):
        """Test the order_book computed field"""
        orders = [
            {"id": 1, "sender": 100, "price": 50.0, "quantity": 10.0, "type": "bid", "condition": 1},
            {"id": 2, "sender": 200, "price": 55.0, "quantity": 5.0, "type": "ask", "condition": 1},
            {"id": 3, "sender": 300, "price": 48.0, "quantity": 8.0, "type": "bid", "condition": 1},
            {"id": 4, "sender": 400, "price": 52.0, "quantity": 3.0, "type": "ask", "condition": 1},
        ]

        for order_data in orders:
            market_state.process_event("add-order", {"order": order_data})

        order_book = market_state.order_book

        # Order book should be a string representation
        assert isinstance(order_book, str)
        # Should contain string representations of all orders
        assert len(order_book.split("\n")) == 4

    def test_order_book_sorting(self, market_state):
        """Test that order book sorts asks and bids correctly"""
        orders = [
            {"id": 1, "sender": 100, "price": 50.0, "quantity": 10.0, "type": "bid", "condition": 1},
            {"id": 2, "sender": 200, "price": 60.0, "quantity": 5.0, "type": "ask", "condition": 1},
            {"id": 3, "sender": 300, "price": 45.0, "quantity": 8.0, "type": "bid", "condition": 1},
            {"id": 4, "sender": 400, "price": 55.0, "quantity": 3.0, "type": "ask", "condition": 1},
        ]

        for order_data in orders:
            market_state.process_event("add-order", {"order": order_data})

        # Get the order book
        order_book_lines = market_state.order_book.split("\n")

        # The order should be: asks (highest to lowest), then bids (highest to lowest)
        # Asks: 60.0 (id=2), 55.0 (id=4)
        # Bids: 50.0 (id=1), 45.0 (id=3)
        assert "price=60.0" in order_book_lines[0]  # Highest ask
        assert "price=55.0" in order_book_lines[1]  # Lower ask
        assert "price=50.0" in order_book_lines[2]  # Highest bid
        assert "price=45.0" in order_book_lines[3]  # Lower bid

    def test_process_unknown_event(self, market_state):
        """Test that unknown events are ignored"""
        initial_orders = len(market_state.orders)
        initial_trades = len(market_state.trades)

        market_state.process_event("unknown-event", {"data": "some data"})

        assert len(market_state.orders) == initial_orders
        assert len(market_state.trades) == initial_trades

    def test_complex_workflow(self, market_state):
        """Test a complex workflow with multiple operations"""
        # Add initial orders
        orders = [
            {"id": 1, "sender": 100, "price": 50.0, "quantity": 10.0, "type": "bid", "condition": 1},
            {"id": 2, "sender": 200, "price": 55.0, "quantity": 5.0, "type": "ask", "condition": 1},
        ]

        for order_data in orders:
            market_state.process_event("add-order", {"order": order_data})

        assert len(market_state.orders) == 2

        # Simulate a trade
        trade_data = {
            "from": 100,
            "to": 200,
            "price": 52.5,
            "quantity": 5.0,
            "condition": 1,
        }
        market_state.process_event("contract-fulfilled", trade_data)

        # Update the bid order (partial fill)
        market_state.process_event("update-order", {"order": {"id": 1, "quantity": 5.0}})

        # Delete the ask order (fully filled)
        market_state.process_event("delete-order", {"order": {"id": 2}})

        # Verify final state
        assert len(market_state.orders) == 1
        assert market_state.orders[1].quantity == 5.0
        assert len(market_state.trades) == 1
        assert market_state.trades[0].price == 52.5
