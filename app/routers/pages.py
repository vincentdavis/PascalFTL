"""HTTP and WebSocket routes for PFTL pages using FastAPI and HTMX.

This module defines the web UI flows:
- Home/leaderboard
- Create game (choose 2-4 players, host name) -> invite link
- Join game (enter name via invite code)
- Configure ship + upgrades (with tokens)
- Waiting room (players + ready states, host can start)
- Game page (dashboards + websocket battle log)
- Game over page
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..game import manager
from ..models import Game, GamePlayer, GameStatusEnum, PlayerUpgrade, ShipType, UpgradeType
from ..utils import generate_code

router = APIRouter()


# Helpers

def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _get_game(db: Session, code: str) -> Game:
    game = db.execute(select(Game).where(Game.code == code)).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


def _player_stats_from(ship: ShipType, upgrades: List[UpgradeType]) -> dict:
    """Compute player stats from base ship and selected upgrades."""
    d = dict(
        health=ship.base_health,
        shields=ship.base_shields,
        power=ship.base_power,
        speed=ship.base_speed,
        fuel=ship.base_fuel,
        cargo_capacity=ship.base_cargo_capacity,
        cargo_space=0,
        weapons=ship.base_weapons,
    )
    for u in upgrades:
        d["health"] += u.delta_health
        d["shields"] += u.delta_shields
        d["power"] += u.delta_power
        d["speed"] += u.delta_speed
        d["fuel"] += u.delta_fuel
        d["cargo_capacity"] += u.delta_cargo_capacity
        d["weapons"] += u.delta_weapons
    return d


# Routes


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Home page with simple leaderboard and create/join options."""
    templates = _templates(request)
    # Last 10 completed games
    recent = db.execute(
        select(Game).where(Game.status == GameStatusEnum.COMPLETED).order_by(Game.completed_at.desc()).limit(10)
    ).scalars().all()

    # Top winners by count
    winners = db.execute(
        select(Game.winner_name, func.count(Game.id)).where(Game.status == GameStatusEnum.COMPLETED)
        .group_by(Game.winner_name).order_by(func.count(Game.id).desc()).limit(5)
    ).all()

    return templates.TemplateResponse(
        "home.html",
        {"request": request, "recent": recent, "winners": winners},
    )


@router.get("/create", response_class=HTMLResponse)
async def create_get(request: Request) -> HTMLResponse:
    templates = _templates(request)
    return templates.TemplateResponse("create_game.html", {"request": request})


@router.post("/create")
async def create_post(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    form = await request.form()
    max_players = int(form.get("max_players", 2))
    host_name = (form.get("host_name") or "Host").strip()[:100]
    if max_players < 2 or max_players > 4:
        max_players = 2

    code = generate_code(6)
    game = Game(code=code, max_players=max_players, status=GameStatusEnum.WAITING)
    db.add(game)
    db.flush()

    host = GamePlayer(game=game, name=host_name, is_host=True)
    db.add(host)
    db.commit()

    return RedirectResponse(url=f"/configure?code={code}&player_id={host.id}", status_code=303)


@router.get("/join/{code}", response_class=HTMLResponse)
async def join_get(request: Request, code: str, db: Session = Depends(get_db)) -> HTMLResponse:
    templates = _templates(request)
    game = _get_game(db, code)
    return templates.TemplateResponse("join.html", {"request": request, "game": game})


@router.post("/join/{code}")
async def join_post(request: Request, code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    form = await request.form()
    name = (form.get("name") or "Player").strip()[:100]
    game = _get_game(db, code)
    if len(game.players) >= game.max_players:
        raise HTTPException(status_code=400, detail="Game is full")
    player = GamePlayer(game=game, name=name)
    db.add(player)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Name already taken in this game")

    return RedirectResponse(url=f"/configure?code={code}&player_id={player.id}", status_code=303)


@router.get("/configure", response_class=HTMLResponse)
async def configure_get(
    request: Request,
    code: str,
    player_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    templates = _templates(request)
    game = _get_game(db, code)
    player = db.get(GamePlayer, player_id)
    if not player or player.game_id != game.id:
        raise HTTPException(status_code=404, detail="Player not found")

    # Load DB ships and upgrades
    ships_db = db.execute(select(ShipType).order_by(ShipType.name)).scalars().all()
    upgrades = db.execute(select(UpgradeType).order_by(UpgradeType.name)).scalars().all()

    # Build a list of card view models based on ships defined in app.ships
    from ..ships import SHIPS
    import os

    # Map DB ships by normalized name for id/cost lookup
    db_by_name = {s.name.strip().lower(): s for s in ships_db}

    def resolve_image_filename(name: str) -> str:
        # Try several naming variants in templates/images/ship_images
        base_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "images", "ship_images")
        candidates = []
        base = name.strip()
        # Original, Title, Upper, Lower
        candidates.extend([
            f"{base}.png",
            f"{base.title()}.png",
            f"{base.upper()}.png",
            f"{base.lower()}.png",
        ])
        # Replace underscores with spaces and spaces with underscores, try common variants
        base_spaces = base.replace("_", " ")
        base_unders = base.replace(" ", "_")
        for b in {base_spaces, base_unders}:
            candidates.extend([
                f"{b}.png",
                f"{b.title()}.png",
                f"{b.upper()}.png",
                f"{b.lower()}.png",
            ])
        # Also try fully uppercased underscored form (our convention)
        candidates.append(base_spaces.upper().replace(" ", "_") + ".png")
        # Deduplicate while preserving order
        seen = set()
        dedup = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                dedup.append(c)
        for cand in dedup:
            p = os.path.join(base_dir, cand)
            if os.path.exists(p):
                return cand
        # Fallback default
        return None

    ship_cards = []
    for ship in SHIPS.values():
        nm = ship.name
        db_ship = db_by_name.get(nm.strip().lower())
        # Compute image filename preference: use ship.image_filename if set; else resolve by name
        img = ship.image_filename or resolve_image_filename(nm)
        # Build URL path for template; if None, use default background
        if img:
            image_url = f"/templates/images/ship_images/{img}"
        else:
            image_url = "/templates/images/pascals_ftl_ship_background.png"
        ship_cards.append(
            {
                "name": nm,
                "id": db_ship.id if db_ship else None,
                # Use DB-defined cost so frontend estimate matches backend validation
                "cost": (db_ship.cost if db_ship else ship.price),
                "image_url": image_url,
                "weight": ship.weight,
                "weight_capacity": ship.weight_capacity,
                "space_capacity": ship.space_capacity,
                "hull_strength": ship.hull_strength,
                "shields": ship.shields,
                "power_capacity": ship.power_capacity,
                "crew": ship.crew,
                "lasers": ship.lasers,
                "railguns": ship.railguns,
                "missiles": ship.missiles,
                "nuclear_weapons": ship.nuclear_weapons,
                "emp": ship.emp,
            }
        )

    return templates.TemplateResponse(
        "configure.html",
        {
            "request": request,
            "game": game,
            "player": player,
            "ship_cards": ship_cards,
            "upgrades": upgrades,
        },
    )


@router.post("/configure")
async def configure_post(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    form = await request.form()
    code = form.get("code")
    player_id = int(form.get("player_id"))
    ship_type_id = int(form.get("ship_type_id"))
    upgrade_ids = form.getlist("upgrade_ids") if hasattr(form, "getlist") else []
    upgrade_ids = [int(u) for u in upgrade_ids]

    game = _get_game(db, code)
    player = db.get(GamePlayer, player_id)
    if not player or player.game_id != game.id:
        raise HTTPException(status_code=404, detail="Player not found")

    ship = db.get(ShipType, ship_type_id)
    if not ship:
        raise HTTPException(status_code=404, detail="Ship type not found")

    sel_upgrades = db.execute(select(UpgradeType).where(UpgradeType.id.in_(upgrade_ids))).scalars().all()

    total_cost = ship.cost + sum(u.cost for u in sel_upgrades)
    budget = 100
    if total_cost > budget:
        raise HTTPException(status_code=400, detail="Not enough tokens for selection")

    # Update player selections
    player.ship_type = ship
    for pu in list(player.upgrades):
        db.delete(pu)
    for u in sel_upgrades:
        db.add(PlayerUpgrade(player=player, upgrade=u))

    stats = _player_stats_from(ship, sel_upgrades)
    player.health = stats["health"]
    player.shields = stats["shields"]
    player.power = stats["power"]
    player.speed = stats["speed"]
    player.fuel = stats["fuel"]
    player.cargo_capacity = stats["cargo_capacity"]
    player.cargo_space = stats["cargo_space"]
    player.weapons = stats["weapons"]
    player.tokens = budget - total_cost
    db.commit()

    return RedirectResponse(url=f"/lobby/{code}?player_id={player.id}", status_code=303)


@router.get("/lobby/{code}", response_class=HTMLResponse)
async def lobby(request: Request, code: str, player_id: Optional[int] = None, db: Session = Depends(get_db)) -> HTMLResponse:
    templates = _templates(request)
    game = _get_game(db, code)
    player = db.get(GamePlayer, int(player_id)) if player_id else None
    return templates.TemplateResponse(
        "lobby.html",
        {"request": request, "game": game, "player": player},
    )


@router.get("/fragment/lobby_players", response_class=HTMLResponse)
async def lobby_players_fragment(request: Request, code: str, db: Session = Depends(get_db)) -> HTMLResponse:
    templates = _templates(request)
    game = _get_game(db, code)
    return templates.TemplateResponse("fragments/lobby_players.html", {"request": request, "game": game})


@router.get("/fragment/lobby_controls", response_class=HTMLResponse)
async def lobby_controls_fragment(
    request: Request, code: str, player_id: Optional[int] = None, db: Session = Depends(get_db)
) -> HTMLResponse:
    templates = _templates(request)
    game = _get_game(db, code)
    player = db.get(GamePlayer, int(player_id)) if player_id else None
    return templates.TemplateResponse(
        "fragments/lobby_controls.html", {"request": request, "game": game, "player": player}
    )


@router.post("/ready")
async def toggle_ready(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    form = await request.form()
    code = form.get("code")
    player_id = int(form.get("player_id"))
    ready = form.get("ready") == "1"

    game = _get_game(db, code)
    player = db.get(GamePlayer, player_id)
    if not player or player.game_id != game.id:
        raise HTTPException(status_code=404, detail="Player not found")
    player.ready = ready
    db.commit()

    templates = _templates(request)
    return templates.TemplateResponse("fragments/ready_button.html", {"request": request, "player": player, "code": code})


@router.post("/start/{code}")
async def start_game(request: Request, code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    form = await request.form()
    player_id = int(form.get("player_id"))
    game = _get_game(db, code)
    host = db.get(GamePlayer, player_id)
    if not host or host.game_id != game.id or not host.is_host:
        raise HTTPException(status_code=403, detail="Only host can start the game")

    if len(game.players) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players to start")
    if not all(p.ready for p in game.players):
        raise HTTPException(status_code=400, detail="All players must be ready")

    from datetime import datetime
    game.status = GameStatusEnum.ACTIVE
    game.started_at = datetime.utcnow()
    db.commit()

    # Initialize manual turn-based game (no auto-sim)
    # Set the first turn to the host by convention; clients will render controls accordingly.
    # For now we just redirect to the game page; actions are performed via manual controls.
    return RedirectResponse(url=f"/game/{code}?player_id={player_id}", status_code=303)


@router.get("/game/{code}", response_class=HTMLResponse)
async def game_page(request: Request, code: str, player_id: Optional[int] = None, db: Session = Depends(get_db)) -> HTMLResponse:
    templates = _templates(request)
    game = _get_game(db, code)
    return templates.TemplateResponse("game.html", {"request": request, "game": game, "player_id": player_id})


@router.get("/fragment/game_players", response_class=HTMLResponse)
async def game_players_fragment(request: Request, code: str, db: Session = Depends(get_db)) -> HTMLResponse:
    """Fragment rendering of the players' ship cards with baseline vs current stats."""
    templates = _templates(request)
    game = _get_game(db, code)
    # Pre-compute baselines per player to avoid complex jinja expressions
    players_data = []
    for p in game.players:
        baseline = None
        if p.ship_type:
            upgrades = [pu.upgrade for pu in p.upgrades]
            baseline = _player_stats_from(p.ship_type, upgrades)
        players_data.append({"player": p, "baseline": baseline})
    context = {"request": request, "game": game, "players_data": players_data}
    return templates.TemplateResponse("fragments/game_players.html", context)


@router.websocket("/ws/{code}")
async def game_ws(websocket: WebSocket, code: str, db: Session = Depends(get_db)) -> None:
    await websocket.accept()
    queue = await manager.connect(code)
    try:
        while True:
            msg = await queue.get()
            await websocket.send_text(msg)
            if msg == "__END__":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(code, queue)
        await websocket.close()


@router.get("/fragment/lobby_check", response_class=HTMLResponse)
async def lobby_check(request: Request, code: str, player_id: Optional[int] = None, db: Session = Depends(get_db)) -> HTMLResponse:
    """HTMX poll endpoint: when the game becomes ACTIVE, instruct client to redirect to the game page.

    HTMX honors the HX-Redirect response header and navigates the browser accordingly.
    We include player_id in the redirect if available so the game page can keep player context.
    """
    game = _get_game(db, code)
    if game.status == GameStatusEnum.ACTIVE:
        dest = f"/game/{code}"
        if player_id:
            dest += f"?player_id={int(player_id)}"
        # Return an empty body but set HX-Redirect so HTMX will navigate
        return HTMLResponse(content="", headers={"HX-Redirect": dest})
    # No redirect; return a tiny no-op
    return HTMLResponse("")


@router.get("/game_over/{code}", response_class=HTMLResponse)
async def game_over(request: Request, code: str, db: Session = Depends(get_db)) -> HTMLResponse:
    templates = _templates(request)
    game = _get_game(db, code)
    if game.status != GameStatusEnum.COMPLETED:
        # If not completed, redirect to game page
        return RedirectResponse(url=f"/game/{code}", status_code=303)
    return templates.TemplateResponse("game_over.html", {"request": request, "game": game})


@router.get("/fragment/game_actions", response_class=HTMLResponse)
async def game_actions_fragment(request: Request, code: str, player_id: Optional[int] = None, db: Session = Depends(get_db)) -> HTMLResponse:
    templates = _templates(request)
    game = _get_game(db, code)
    # Compute available weapons for the current player's ship using app.ships metadata
    available_weapons = []
    weapon_labels = {
        "lasers": "Lasers",
        "railguns": "Railguns",
        "missiles": "Missiles",
        "nuclear_weapons": "Nuclear",
        "emp": "EMP",
    }
    try:
        if player_id:
            me = db.get(GamePlayer, int(player_id))
            if me and me.ship_type and me.ship_type.name:
                from ..ships import SHIPS
                key = me.ship_type.name
                ship = SHIPS.get(key) or SHIPS.get(key.title()) or SHIPS.get(key.upper())
                if ship:
                    for k in ["lasers", "railguns", "missiles", "nuclear_weapons", "emp"]:
                        if getattr(ship, k, 0) > 0:
                            available_weapons.append({"key": k, "label": weapon_labels[k]})
    except Exception:
        # Best-effort; fallback to lasers only if any error
        available_weapons = [{"key": "lasers", "label": weapon_labels["lasers"]}]
    return templates.TemplateResponse(
        "fragments/game_actions.html",
        {"request": request, "game": game, "player_id": player_id, "available_weapons": available_weapons},
    )


@router.post("/action/attack", response_class=HTMLResponse)
async def action_attack(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    form = await request.form()
    code = str(form.get("code"))
    attacker_id = int(form.get("player_id"))
    target_id = int(form.get("target_id"))
    weapon = (form.get("weapon") or "lasers").strip()

    game = _get_game(db, code)
    attacker = db.get(GamePlayer, attacker_id)
    target = db.get(GamePlayer, target_id)
    if not attacker or attacker.game_id != game.id:
        raise HTTPException(status_code=404, detail="Attacker not found")
    if not target or target.game_id != game.id:
        raise HTTPException(status_code=404, detail="Target not found")
    if game.status != GameStatusEnum.ACTIVE:
        raise HTTPException(status_code=400, detail="Game not active")
    if attacker.health <= 0:
        raise HTTPException(status_code=400, detail="You are destroyed")
    if target.health <= 0:
        raise HTTPException(status_code=400, detail="Target already destroyed")

    # Resolve attack with weapon flavor
    import random
    weapon_names = {
        "lasers": "Lasers",
        "railguns": "Railguns",
        "missiles": "Missiles",
        "nuclear_weapons": "Nuclear",
        "emp": "EMP",
    }
    await manager.broadcast(code, f"{attacker.name} attacks {target.name} with {weapon_names.get(weapon, 'Lasers')}.\n")

    miss_chance = min(60, max(5, 20 + (target.speed - attacker.speed) // 2))
    if random.randint(1, 100) <= miss_chance:
        await manager.broadcast(code, f"{attacker.name} missed {target.name}!\n")
    else:
        base = attacker.weapons + attacker.power // 2 + (attacker.ship_type.base_crew if attacker.ship_type else 1)
        # Simple multipliers per weapon type
        mult = {
            "lasers": 1.00,
            "railguns": 1.15,
            "missiles": 1.25,
            "nuclear_weapons": 1.60,
            "emp": 0.60,
        }.get(weapon, 1.0)
        if weapon == "emp":
            # EMP primarily drains shields; minimal hull damage if shields are down
            if target.shields > 0:
                drain = max(5, int(base * 1.2))
                absorbed = min(target.shields, drain)
                target.shields -= absorbed
                await manager.broadcast(code, f"EMP drains {absorbed} shields from {target.name}.\n")
                dmg = 0
            else:
                dmg = 5
        else:
            dmg = max(5, int(base * mult * random.uniform(0.6, 1.1)))
            if target.shields > 0:
                # New rule: while shields > 0, ALL damage is absorbed by shields; no spillover to hull
                absorbed = min(target.shields, dmg)
                target.shields -= absorbed
                await manager.broadcast(code, f"{attacker.name} hits {target.name}'s shields for {absorbed}.\n")
                dmg = 0
        if dmg > 0:
            target.health -= dmg
            await manager.broadcast(code, f"{attacker.name} deals {dmg} hull damage to {target.name}.\n")
        if target.health <= 0:
            await manager.broadcast(code, f"{target.name} has been destroyed!\n")

    # Check win condition
    alive = [p for p in game.players if p.health > 0]
    if len(alive) <= 1:
        from datetime import datetime
        game.status = GameStatusEnum.COMPLETED
        if alive:
            game.winner_name = alive[0].name
            await manager.broadcast(code, f"Winner: {alive[0].name}!\n")
        game.completed_at = datetime.utcnow()
        await manager.broadcast(code, "__END__")
    else:
        # Shields regeneration step: after each action, regenerate shields for all alive players based on power
        for gp in game.players:
            if gp.health > 0 and gp.ship_type:
                # Compute baseline max shields with upgrades
                upgrades = [pu.upgrade for pu in gp.upgrades]
                baseline = _player_stats_from(gp.ship_type, upgrades)
                max_shields = baseline.get("shields", gp.shields)
                if gp.shields < max_shields and gp.power > 0:
                    # Regen rate: 20% of current power, at least 1
                    import math
                    regen = max(1, math.ceil(gp.power * 0.2))
                    new_val = min(max_shields, gp.shields + regen)
                    gained = new_val - gp.shields
                    if gained > 0:
                        gp.shields = new_val
                        await manager.broadcast(code, f"{gp.name}'s shields regenerate by {gained} (→ {gp.shields}/{max_shields}).\n")
    db.commit()
    # After committing state changes, send a lightweight refresh ping if game continues
    if game.status == GameStatusEnum.ACTIVE:
        await manager.broadcast(code, "__REFRESH__")

    # Recompute available weapons for the fragment
    available_weapons = []
    try:
        if attacker and attacker.ship_type and attacker.ship_type.name:
            from ..ships import SHIPS
            key = attacker.ship_type.name
            ship = SHIPS.get(key) or SHIPS.get(key.title()) or SHIPS.get(key.upper())
            labels = {"lasers": "Lasers", "railguns": "Railguns", "missiles": "Missiles", "nuclear_weapons": "Nuclear", "emp": "EMP"}
            if ship:
                for k in ["lasers", "railguns", "missiles", "nuclear_weapons", "emp"]:
                    if getattr(ship, k, 0) > 0:
                        available_weapons.append({"key": k, "label": labels[k]})
    except Exception:
        pass

    templates = _templates(request)
    return templates.TemplateResponse(
        "fragments/game_actions.html",
        {"request": request, "game": game, "player_id": attacker_id, "available_weapons": available_weapons},
    )


@router.post("/action/skip", response_class=HTMLResponse)
async def action_skip(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    form = await request.form()
    code = str(form.get("code"))
    player_id = int(form.get("player_id"))
    game = _get_game(db, code)
    player = db.get(GamePlayer, player_id)
    if not player or player.game_id != game.id:
        raise HTTPException(status_code=404, detail="Player not found")
    if game.status != GameStatusEnum.ACTIVE:
        raise HTTPException(status_code=400, detail="Game not active")

    await manager.broadcast(code, f"{player.name} skipped their turn.\n")
    # Shields regeneration after a turn passes
    for gp in game.players:
        if gp.health > 0 and gp.ship_type:
            upgrades = [pu.upgrade for pu in gp.upgrades]
            baseline = _player_stats_from(gp.ship_type, upgrades)
            max_shields = baseline.get("shields", gp.shields)
            if gp.shields < max_shields and gp.power > 0:
                import math
                regen = max(1, math.ceil(gp.power * 0.2))
                new_val = min(max_shields, gp.shields + regen)
                gained = new_val - gp.shields
                if gained > 0:
                    gp.shields = new_val
                    await manager.broadcast(code, f"{gp.name}'s shields regenerate by {gained} (→ {gp.shields}/{max_shields}).\n")
    db.commit()
    # After committing state changes, send a lightweight refresh ping
    if game.status == GameStatusEnum.ACTIVE:
        await manager.broadcast(code, "__REFRESH__")

    templates = _templates(request)
    # Recompute available weapons for the fragment
    available_weapons = []
    try:
        if player and player.ship_type and player.ship_type.name:
            from ..ships import SHIPS
            key = player.ship_type.name
            ship = SHIPS.get(key) or SHIPS.get(key.title()) or SHIPS.get(key.upper())
            labels = {"lasers": "Lasers", "railguns": "Railguns", "missiles": "Missiles", "nuclear_weapons": "Nuclear", "emp": "EMP"}
            if ship:
                for k in ["lasers", "railguns", "missiles", "nuclear_weapons", "emp"]:
                    if getattr(ship, k, 0) > 0:
                        available_weapons.append({"key": k, "label": labels[k]})
    except Exception:
        pass
    return templates.TemplateResponse("fragments/game_actions.html", {"request": request, "game": game, "player_id": player_id, "available_weapons": available_weapons})
