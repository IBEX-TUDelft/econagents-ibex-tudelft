"""
Shared argument parser for all game run scripts.

Each game's run_game.py calls base_parser() to get a pre-populated parser
with common arguments, then adds its own game-specific arguments on top.
"""

import argparse


def base_parser(description: str = "Run agents against a running game-engine instance.") -> argparse.ArgumentParser:
    """
    Return an ArgumentParser pre-populated with arguments common to all games.

    Games add their own arguments after calling this:

        parser = base_parser("Run harberger agents.")
        parser.add_argument("--specs", ...)
        args = parser.parse_args()
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--personality",
        default=None,
        metavar="NAME",
        help="Persona to use (looks in prompts/personas/<NAME>/ before falling back to generic prompts)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    return parser
