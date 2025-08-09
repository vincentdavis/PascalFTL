"""ORM models for PFTL game using SQLAlchemy 2.0 style.

The domain is intentionally simplified for a minimal-yet-functional game per guidelines.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class GameStatusEnum(str):
    """String enum class for game status values."""

    WAITING = "waiting"
    ACTIVE = "active"
    COMPLETED = "completed"


class ShipType(Base):
    """A selectable ship archetype with base stats and token cost."""

    __tablename__ = "ship_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    cost: Mapped[int] = mapped_column(Integer, default=50)

    base_health: Mapped[int] = mapped_column(Integer, default=100)
    base_shields: Mapped[int] = mapped_column(Integer, default=50)
    base_power: Mapped[int] = mapped_column(Integer, default=20)
    base_speed: Mapped[int] = mapped_column(Integer, default=20)
    base_fuel: Mapped[int] = mapped_column(Integer, default=100)
    base_cargo_capacity: Mapped[int] = mapped_column(Integer, default=10)
    base_weapons: Mapped[int] = mapped_column(Integer, default=20)
    base_crew: Mapped[int] = mapped_column(Integer, default=5)

    upgrades: Mapped[list["UpgradeType"]] = relationship(back_populates="ship_type")


class UpgradeType(Base):
    """An upgrade that can be applied to a player's ship, modifying stats."""

    __tablename__ = "upgrade_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    cost: Mapped[int] = mapped_column(Integer, default=10)

    # Optional association - if not null, upgrade is intended for a specific ship archetype
    ship_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ship_types.id"), nullable=True)
    ship_type: Mapped[Optional[ShipType]] = relationship(back_populates="upgrades")

    delta_health: Mapped[int] = mapped_column(Integer, default=0)
    delta_shields: Mapped[int] = mapped_column(Integer, default=0)
    delta_power: Mapped[int] = mapped_column(Integer, default=0)
    delta_speed: Mapped[int] = mapped_column(Integer, default=0)
    delta_fuel: Mapped[int] = mapped_column(Integer, default=0)
    delta_cargo_capacity: Mapped[int] = mapped_column(Integer, default=0)
    delta_weapons: Mapped[int] = mapped_column(Integer, default=0)


class Game(Base):
    """A game session identified by a short code and composed of players."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    max_players: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String(16), default=GameStatusEnum.WAITING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    winner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    players: Mapped[list["GamePlayer"]] = relationship(back_populates="game", cascade="all, delete-orphan")


class GamePlayer(Base):
    """A player participating in a specific game with selections and state."""

    __tablename__ = "game_players"
    __table_args__ = (
        UniqueConstraint("game_id", "name", name="uq_game_player_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))

    # Configuration
    tokens: Mapped[int] = mapped_column(Integer, default=100)
    ready: Mapped[bool] = mapped_column(Boolean, default=False)
    is_host: Mapped[bool] = mapped_column(Boolean, default=False)

    ship_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ship_types.id"), nullable=True)
    ship_type: Mapped[Optional[ShipType]] = relationship()

    # Current stats
    health: Mapped[int] = mapped_column(Integer, default=0)
    shields: Mapped[int] = mapped_column(Integer, default=0)
    power: Mapped[int] = mapped_column(Integer, default=0)
    speed: Mapped[int] = mapped_column(Integer, default=0)
    fuel: Mapped[int] = mapped_column(Integer, default=0)
    cargo_capacity: Mapped[int] = mapped_column(Integer, default=0)
    cargo_space: Mapped[int] = mapped_column(Integer, default=0)
    weapons: Mapped[int] = mapped_column(Integer, default=0)

    game: Mapped[Game] = relationship(back_populates="players")
    upgrades: Mapped[list["PlayerUpgrade"]] = relationship(back_populates="player", cascade="all, delete-orphan")


class PlayerUpgrade(Base):
    """Mapping of upgrades selected by a specific game player."""

    __tablename__ = "player_upgrades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("game_players.id"), index=True)
    upgrade_id: Mapped[int] = mapped_column(ForeignKey("upgrade_types.id"))

    player: Mapped[GamePlayer] = relationship(back_populates="upgrades")
    upgrade: Mapped[UpgradeType] = relationship()
