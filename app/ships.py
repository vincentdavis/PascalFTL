"""The file defines models for ships and defines the available ships.

This module provides a lightweight Pydantic model for Ship and a set of predefined
ship instances (one per ShipType) that can be used for demos, configuration UIs,
or offline simulations. The main game persists ship archetypes via SQLAlchemy in
app.models and seeds them in app.seed.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ShipType(str):
    """String enum class for ship types"""

    BATTLESHIP = "Battleship"
    DESTROYER = "Destroyer"
    FLYING_SAUCERS = "Flying Saucers"
    CRUISER = "Cruiser"
    STARDESTROYER = "Star Destroyer"
    STARFIGHTER = "Starfighter"
    SERAPH = "Seraph"
    YAMATO = "Yamato"
    DEFENDER = "Defender"


class Ship(BaseModel):
    """Ship model representing a concrete ship with stats and loadouts."""

    ship_id: UUID = Field(default_factory=uuid4)
    type: str
    name: str  # The user can later override/set the ship name
    price: int  # Price of the ship
    weight: str  # The ship's weight class/category (e.g., light/medium/heavy)
    weight_capacity: int  # How much weight can the ship carry?

    # Optional image file name (relative to templates/images/ship_images). If None, a default image is used.
    image_filename: str | None = None

    hull_strength: int
    hull_damage: int

    space_capacity: int  # How much space does the ship have for extra modules?

    shields: int
    shield_damage: int
    electronic_defense: int  # The power of electronic defence systemizes

    power_capacity: int  # The power output of the ship's generator
    power_damage: int

    crew: int

    # Weapons
    lasers: int  # the number or strength of the lasers
    railguns: int  # the number or strength of the railguns
    missiles: int  # the number or strength of the missiles
    nuclear_weapons: int  # the number or strength of the nuclear weapons
    emp: int  # the number or strength of the electro magnetic pulse


# Predefined ship instances for each ShipType
BATTLESHIP: Ship = Ship(
    type=ShipType.BATTLESHIP,
    name=ShipType.BATTLESHIP,
    price=25,
    weight="heavy",
    weight_capacity=200,
    hull_strength=180,
    hull_damage=0,
    space_capacity=20,
    shields=120,
    shield_damage=0,
    electronic_defense=50,
    power_capacity=40,
    power_damage=0,
    crew=20,
    lasers=6,
    railguns=2,
    missiles=8,
    nuclear_weapons=1,
    emp=10,
)

DESTROYER: Ship = Ship(
    type=ShipType.DESTROYER,
    name=ShipType.DESTROYER,
    price=20,
    weight="heavy",
    weight_capacity=170,
    hull_strength=160,
    hull_damage=0,
    space_capacity=18,
    shields=100,
    shield_damage=0,
    electronic_defense=50,
    power_capacity=35,
    power_damage=0,
    crew=15,
    lasers=5,
    railguns=2,
    missiles=6,
    nuclear_weapons=0,
    emp=10,
)

FLYING_SAUCERS: Ship = Ship(
    type=ShipType.FLYING_SAUCERS,
    name=ShipType.FLYING_SAUCERS,
    price=15,
    weight="light",
    weight_capacity=90,
    hull_strength=120,
    hull_damage=0,
    space_capacity=12,
    shields=80,
    shield_damage=0,
    electronic_defense=50,
    power_capacity=30,
    power_damage=0,
    crew=5,
    lasers=4,
    railguns=0,
    missiles=2,
    nuclear_weapons=0,
    emp=10,
)

CRUISER: Ship = Ship(
    type=ShipType.CRUISER,
    name=ShipType.CRUISER,
    price=20,
    weight="medium",
    weight_capacity=150,
    hull_strength=150,
    hull_damage=0,
    space_capacity=18,
    shields=90,
    shield_damage=0,
    electronic_defense=50,
    power_capacity=32,
    power_damage=0,
    crew=12,
    lasers=5,
    railguns=1,
    missiles=4,
    nuclear_weapons=0,
    emp=10,
)

STARDESTROYER: Ship = Ship(
    type=ShipType.STARDESTROYER,
    name=ShipType.STARDESTROYER,
    price=30,
    weight="super-heavy",
    weight_capacity=300,
    hull_strength=220,
    hull_damage=0,
    space_capacity=25,
    shields=150,
    shield_damage=0,
    electronic_defense=50,
    power_capacity=60,
    power_damage=0,
    crew=50,
    lasers=10,
    railguns=4,
    missiles=12,
    nuclear_weapons=2,
    emp=10,
)

STARFIGHTER: Ship = Ship(
    type=ShipType.STARFIGHTER,
    name=ShipType.STARFIGHTER,
    price=10,
    weight="light",
    weight_capacity=80,
    hull_strength=100,
    hull_damage=0,
    space_capacity=8,
    shields=60,
    shield_damage=0,
    electronic_defense=50,
    power_capacity=24,
    power_damage=0,
    crew=1,
    lasers=2,
    railguns=0,
    missiles=2,
    nuclear_weapons=0,
    emp=10,
)

SERAPH: Ship = Ship(
    type=ShipType.SERAPH,
    name=ShipType.SERAPH,
    price=20,
    weight="medium",
    weight_capacity=120,
    hull_strength=130,
    hull_damage=0,
    space_capacity=14,
    shields=85,
    shield_damage=0,
    electronic_defense=50,
    power_capacity=34,
    power_damage=0,
    crew=8,
    lasers=4,
    railguns=1,
    missiles=3,
    nuclear_weapons=0,
    emp=10,
)

YAMATO: Ship = Ship(
    type=ShipType.YAMATO,
    name=ShipType.YAMATO,
    price=20,
    weight="heavy",
    weight_capacity=190,
    hull_strength=170,
    hull_damage=0,
    space_capacity=19,
    shields=110,
    shield_damage=0,
    electronic_defense=50,
    power_capacity=38,
    power_damage=0,
    crew=18,
    lasers=6,
    railguns=2,
    missiles=6,
    nuclear_weapons=1,
    emp=10,
)

DEFENDER = Ship(
    type=ShipType.DEFENDER,
    name=ShipType.DEFENDER,
    price=20,
    weight="heavy",
    weight_capacity=200,
    hull_strength=200,
    hull_damage=0,
    space_capacity=18,
    shields=150,
    shield_damage=0,
    electronic_defense=50,
    power_capacity=50,
    power_damage=0,
    crew=10,
    lasers=2,
    railguns=2,
    missiles=0,
    nuclear_weapons=0,
    emp=10,
)

# A simple lookup for external code
SHIPS = {
    ShipType.BATTLESHIP: BATTLESHIP,
    ShipType.DESTROYER: DESTROYER,
    ShipType.FLYING_SAUCERS: FLYING_SAUCERS,
    ShipType.CRUISER: CRUISER,
    ShipType.STARDESTROYER: STARDESTROYER,
    ShipType.STARFIGHTER: STARFIGHTER,
    ShipType.SERAPH: SERAPH,
    ShipType.YAMATO: YAMATO,
    ShipType.DEFENDER: DEFENDER,
}

__all__ = [
    "BATTLESHIP",
    "CRUISER",
    "DEFENDER",
    "DESTROYER",
    "FLYING_SAUCERS",
    "SERAPH",
    "SHIPS",
    "STARDESTROYER",
    "STARFIGHTER",
    "YAMATO",
    "Ship",
    "ShipType",
]
