"""Seed initial data: ship types and upgrades.

Executed on app startup to ensure required options exist.
"""

from __future__ import annotations

from typing import Iterable

from sqlalchemy import select

from .db import db_session
from .models import ShipType, UpgradeType


def _get_or_create_ship(name: str, **kwargs) -> ShipType:
    with db_session() as db:
        ship = db.execute(select(ShipType).where(ShipType.name == name)).scalar_one_or_none()
        if ship:
            return ship
        ship = ShipType(name=name, **kwargs)
        db.add(ship)
        db.commit()
        db.refresh(ship)
        return ship


def _bulk_create_upgrades(upgrades: Iterable[dict]) -> None:
    with db_session() as db:
        existing = {u.name for u in db.execute(select(UpgradeType)).scalars().all()}
        new_objs = [UpgradeType(**u) for u in upgrades if u["name"] not in existing]
        if new_objs:
            db.add_all(new_objs)
            db.commit()


def seed_initial_data() -> None:
    """Create ship types and upgrades if they don't exist."""
    # Ship types (names per guidelines) with simple varied base stats and costs
    ships_data = [
        ("Battleship", dict(cost=80, base_health=180, base_shields=120, base_power=40, base_speed=10, base_weapons=50, base_cargo_capacity=20, base_crew=20)),
        ("Destroyer", dict(cost=70, base_health=160, base_shields=100, base_power=35, base_speed=15, base_weapons=45, base_cargo_capacity=15, base_crew=15)),
        ("Flying Saucers", dict(cost=60, base_health=120, base_shields=80, base_power=30, base_speed=35, base_weapons=30, base_cargo_capacity=12, base_crew=5)),
        ("Cruiser", dict(cost=65, base_health=150, base_shields=90, base_power=32, base_speed=18, base_weapons=40, base_cargo_capacity=18, base_crew=12)),
        # Additional ships defined in app.ships but previously missing in DB
        ("Star Destroyer", dict(cost=90, base_health=220, base_shields=150, base_power=60, base_speed=8, base_weapons=70, base_cargo_capacity=25, base_crew=50)),
        ("Star Fighter", dict(cost=40, base_health=100, base_shields=60, base_power=24, base_speed=38, base_weapons=28, base_cargo_capacity=8, base_crew=1)),
        ("Seraph", dict(cost=65, base_health=130, base_shields=85, base_power=34, base_speed=22, base_weapons=38, base_cargo_capacity=14, base_crew=8)),
        ("Yamato", dict(cost=70, base_health=170, base_shields=110, base_power=38, base_speed=12, base_weapons=48, base_cargo_capacity=19, base_crew=18)),
        ("Defender", dict(cost=70, base_health=200, base_shields=150, base_power=50, base_speed=14, base_weapons=35, base_cargo_capacity=18, base_crew=10)),
        # Existing classic ships
        ("Patrol", dict(cost=40, base_health=100, base_shields=60, base_power=20, base_speed=25, base_weapons=20, base_cargo_capacity=10, base_crew=6)),
        ("X-Wing", dict(cost=55, base_health=110, base_shields=70, base_power=28, base_speed=30, base_weapons=35, base_cargo_capacity=8, base_crew=1)),
        ("Y-Wing", dict(cost=50, base_health=120, base_shields=80, base_power=25, base_speed=22, base_weapons=38, base_cargo_capacity=10, base_crew=2)),
        ("A-Wing", dict(cost=50, base_health=90, base_shields=50, base_power=24, base_speed=40, base_weapons=28, base_cargo_capacity=6, base_crew=1)),
        ("Millenium Falcon", dict(cost=75, base_health=140, base_shields=85, base_power=35, base_speed=28, base_weapons=42, base_cargo_capacity=25, base_crew=4)),
        ("TIE Fighter", dict(cost=45, base_health=80, base_shields=30, base_power=22, base_speed=35, base_weapons=26, base_cargo_capacity=4, base_crew=1)),
        ("TIE Interceptor", dict(cost=55, base_health=85, base_shields=35, base_power=26, base_speed=42, base_weapons=30, base_cargo_capacity=5, base_crew=1)),
        ("TIE Defender", dict(cost=65, base_health=120, base_shields=90, base_power=32, base_speed=30, base_weapons=38, base_cargo_capacity=6, base_crew=1)),
        ("TIE Bomber", dict(cost=50, base_health=100, base_shields=60, base_power=24, base_speed=20, base_weapons=40, base_cargo_capacity=12, base_crew=1)),
        ("TIE Advanced", dict(cost=60, base_health=110, base_shields=70, base_power=30, base_speed=34, base_weapons=36, base_cargo_capacity=6, base_crew=1)),
        ("TIE Phantom", dict(cost=60, base_health=95, base_shields=50, base_power=28, base_speed=45, base_weapons=33, base_cargo_capacity=6, base_crew=1)),
    ]

    # Ensure ships exist
    for name, params in ships_data:
        _get_or_create_ship(name, **params)

    # Generic upgrades
    upgrades = [
        dict(name="Reinforced Hull", description="+30 health", cost=20, delta_health=30),
        dict(name="Advanced Shields", description="+40 shields", cost=25, delta_shields=40),
        dict(name="Engine Overdrive", description="+10 speed", cost=20, delta_speed=10),
        dict(name="Power Core", description="+10 power", cost=20, delta_power=10),
        dict(name="Extra Fuel Tanks", description="+40 fuel", cost=10, delta_fuel=40),
        dict(name="Cargo Pods", description="+10 cargo capacity", cost=10, delta_cargo_capacity=10),
        dict(name="Laser Cannons", description="+15 weapons", cost=25, delta_weapons=15),
        dict(name="Crew Quarters", description="+3 crew", cost=10, delta_health=0),  # Crew used in sim, no direct stat
    ]

    _bulk_create_upgrades(upgrades)
