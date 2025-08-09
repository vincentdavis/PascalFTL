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

    ships = db.execute(select(ShipType).order_by(ShipType.name)).scalars().all()
    upgrades = db.execute(select(UpgradeType).order_by(UpgradeType.name)).scalars().all()

    return templates.TemplateResponse(
        "configure.html",
        {
            "request": request,
            "game": game,
            "player": player,
            "ships": ships,
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

    # Start sim (fire and forget)
    await manager.run_battle(db, code)

    return RedirectResponse(url=f"/game/{code}?player_id={player_id}", status_code=303)


@router.get("/game/{code}", response_class=HTMLResponse)
async def game_page(request: Request, code: str, player_id: Optional[int] = None, db: Session = Depends(get_db)) -> HTMLResponse:
    templates = _templates(request)
    game = _get_game(db, code)
    return templates.TemplateResponse("game.html", {"request": request, "game": game, "player_id": player_id})


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


@router.get("/game_over/{code}", response_class=HTMLResponse)
async def game_over(request: Request, code: str, db: Session = Depends(get_db)) -> HTMLResponse:
    templates = _templates(request)
    game = _get_game(db, code)
    if game.status != GameStatusEnum.COMPLETED:
        # If not completed, redirect to game page
        return RedirectResponse(url=f"/game/{code}", status_code=303)
    return templates.TemplateResponse("game_over.html", {"request": request, "game": game})
