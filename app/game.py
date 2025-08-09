"""Game manager and battle simulation for PFTL.

This module provides a very simple free-for-all battle simulator supporting 2-4 players.
It broadcasts log lines over websockets to all connected clients for a game code.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Dict, List, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import db_session
from .models import Game, GamePlayer, GameStatusEnum, PlayerUpgrade, UpgradeType


@dataclass
class Fighter:
    """In-memory snapshot of a player's ship for the battle simulation."""

    id: int
    name: str
    health: int
    shields: int
    power: int
    speed: int
    fuel: int
    cargo_capacity: int
    cargo_space: int
    weapons: int
    crew: int

    @property
    def alive(self) -> bool:
        return self.health > 0


class GameManager:
    """Manages websocket connections and runs simulations per game."""

    def __init__(self) -> None:
        self._connections: Dict[str, Set[asyncio.Queue[str]]] = {}
        self._running: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def connect(self, code: str) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._connections.setdefault(code, set()).add(queue)
        return queue

    async def disconnect(self, code: str, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            conns = self._connections.get(code)
            if conns and queue in conns:
                conns.remove(queue)

    async def broadcast(self, code: str, message: str) -> None:
        for q in list(self._connections.get(code, set())):
            await q.put(message)

    async def run_battle(self, db: Session, code: str) -> None:
        """Run a simple battle simulation until one winner remains."""
        if code in self._running:
            return

        async with self._lock:
            if code in self._running:
                return
            task = asyncio.create_task(self._simulate(db, code))
            self._running[code] = task

    async def _simulate(self, db: Session, code: str) -> None:
        try:
            # Load initial game snapshot and build fighters using a fresh session
            with db_session() as s:
                game: Game | None = s.execute(select(Game).where(Game.code == code)).scalar_one_or_none()
                if not game or game.status != GameStatusEnum.ACTIVE:
                    return

                fighters = [
                    Fighter(
                        id=p.id,
                        name=p.name,
                        health=p.health,
                        shields=p.shields,
                        power=p.power,
                        speed=p.speed,
                        fuel=p.fuel,
                        cargo_capacity=p.cargo_capacity,
                        cargo_space=p.cargo_space,
                        weapons=p.weapons,
                        crew=max(1, (p.ship_type.base_crew if p.ship_type else 1)),
                    )
                    for p in game.players
                ]

            await self.broadcast(code, f"Battle started with {len(fighters)} ships!\n")
            round_no = 1
            while sum(1 for f in fighters if f.alive) > 1:
                await self.broadcast(code, f"-- Round {round_no} --\n")
                # Each alive fighter attacks a random other alive fighter
                alive = [f for f in fighters if f.alive]
                random.shuffle(alive)
                for attacker in alive:
                    targets = [f for f in alive if f.id != attacker.id]
                    if not targets:
                        break
                    target = random.choice(targets)
                    # Chance to miss based on target speed
                    miss_chance = min(60, max(5, 20 + (target.speed - attacker.speed) // 2))
                    if random.randint(1, 100) <= miss_chance:
                        await self.broadcast(code, f"{attacker.name} missed {target.name}!\n")
                        continue

                    # Damage based on weapons and power, small randomness and crew bonus
                    base = attacker.weapons + attacker.power // 2 + attacker.crew
                    dmg = max(5, int(base * random.uniform(0.6, 1.1)))

                    # Apply to shields first
                    if target.shields > 0:
                        absorbed = min(target.shields, dmg)
                        target.shields -= absorbed
                        dmg -= absorbed
                        await self.broadcast(code, f"{attacker.name} hits {target.name}'s shields for {absorbed}.\n")
                    if dmg > 0:
                        target.health -= dmg
                        await self.broadcast(code, f"{attacker.name} deals {dmg} hull damage to {target.name}.\n")
                    if target.health <= 0:
                        await self.broadcast(code, f"{target.name} has been destroyed!\n")
                round_no += 1
                await asyncio.sleep(1.0)

            winner = next((f for f in fighters if f.alive), None)
            if winner:
                await self.broadcast(code, f"Winner: {winner.name}!\n")
                # Persist winner using a fresh session
                from datetime import datetime
                with db_session() as s:
                    game = s.execute(select(Game).where(Game.code == code)).scalar_one_or_none()
                    if game:
                        game.status = GameStatusEnum.COMPLETED
                        game.winner_name = winner.name
                        game.completed_at = datetime.utcnow()
            
        finally:
            # Close out
            await self.broadcast(code, "__END__")
            async with self._lock:
                self._running.pop(code, None)


manager = GameManager()
