# econagents IBEX-TUDelft Extension

This package provides IBEX-TUDelft specific functionality for the `econagents` framework, including agent-side market and chat state management and specialized configuration parsers.

## Features

- **MarketState**: Order book management with support for orders and trades
- **ChatState**: Chat state managed directly per agent.
- **IbexTudelftConfigParser**: Extended configuration parser with:
  - Role assignment functionality (assign-name, assign-role events)
  - Market event handlers (add-order, update-order, delete-order, contract-fulfilled)
  - Asset movement event handlers

## Installation

```bash
pip install econagents-ibex-tudelft
```

Or install from source:

```bash
git clone https://github.com/IBEX-TUDelft/econagents-ibex-tudelft.git
cd econagents-ibex-tudelft
pip install -e .
```

## Usage

See examples in the `examples` directory for how to use this package.

## License

MIT License - See LICENSE file for details.
