"""
Run one or more goods_market agents against a running game-engine instance.

Usage:
    python -m examples.goods_market.run_game <game_id> [options]

    python -m examples.goods_market.run_game game_1 --num-agents 3
    python -m examples.goods_market.run_game game_1 --personality aggressive
    python -m examples.goods_market.run_game game_1 --num-agents 2 --personality cautious --log-level DEBUG

Environment variables (set in .env):
    HOSTNAME   Game server host              (default: localhost)
    WS_PORT    WebSocket port               (default: 3088)
    API_PORT   REST API port for /join      (default: 3089)
"""

import argparse
import asyncio
import logging
import os
from typing import Optional

from dotenv import load_dotenv

from examples.args import base_parser
from examples.create_game import join_game
from examples.goods_market.manager import GoodsMarketManager

load_dotenv(override=True)

HOSTNAME = os.getenv("HOSTNAME", "localhost")
WS_PORT = os.getenv("WS_PORT", "3088")


async def run_agent(game_id: str, player_number: Optional[int], personality: Optional[str], log_level: int) -> None:
    slot = join_game(game_id, player_number=player_number)
    confirmed_number: int = slot["playerNumber"]

    manager = GoodsMarketManager(
        game_id=game_id,
        player_number=confirmed_number,
        token=slot["token"],
        personality=personality,
    )
    manager.url = f"ws://{HOSTNAME}:{WS_PORT}"
    manager.logger = _make_logger(confirmed_number, log_level)

    await manager.start()


async def main(args: argparse.Namespace) -> None:
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    player_number: int | None = getattr(args, "player_number", None)
    tasks = [
        asyncio.create_task(
            run_agent(args.game_id, player_number, args.personality, log_level),
            name=f"agent-{i + 1}",
        )
        for i in range(args.num_agents)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for task, result in zip(tasks, results):
        if isinstance(result, BaseException):
            logging.error(f"[{task.get_name()}] failed: {result}", exc_info=result)


def _make_logger(player_number: int, log_level: int) -> logging.Logger:
    logger = logging.getLogger(f"goods_market.agent.{player_number}")
    logger.setLevel(log_level)
    return logger


if __name__ == "__main__":
    parser = base_parser("Run goods_market agents against a running game-engine instance.")
    parser.add_argument("--game-id", required=True, help="ID of the running game to join (e.g. game_1)")
    parser.add_argument("--player-number", type=int, default=None, metavar="N", help="Specific player slot to claim")
    parser.add_argument(
        "--num-agents",
        type=int,
        default=1,
        metavar="N",
        help="Number of agents to spawn (default: 1)",
    )

    asyncio.run(main(parser.parse_args()))
