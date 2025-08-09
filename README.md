# Pascal's Faster Than Light (PFTL)

A space ship battle simulator for 2–4 players. Built with FastAPI, HTMX for dynamic UI updates, WebSockets for live battle
logs, and SQLAlchemy with SQLite (dev) / PostgreSQL (prod) for persistence.

## Features

- Create game (choose 2–4 players) and invite others by shareable link/code
- Join game by code
- Ship selection and configuration with a 100-token budget
- Multiple ship archetypes and upgrades (seeded on first run)
- Waiting room (players list, ready-up toggle, host can start)
- Live battle simulation streamed via WebSocket
- Game over page and simple leaderboard (top winners + recent games)

## Tech Stack

- Python 3.13+
- FastAPI
- HTMX for partial page updates
- WebSockets for streaming battle logs
- SQLAlchemy ORM; SQLite for development (default), PostgreSQL supported
- python-dotenv for environment variables via `.env`

## Getting Started

1. Clone repo and set up env:

```bash
# Using uv (optional):
uv venv
uv pip install -r requirements.txt  # or use pyproject directly via uv

# Using pip:
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

The project uses PEP 621 (pyproject.toml) to declare dependencies. If your tool does not auto-install, run:

```bash
pip install fastapi uvicorn[standard] jinja2 sqlalchemy pydantic python-dotenv
```

2. Configure environment (optional):

```bash
cp .env.example .env
# edit .env as needed
```

3. Run the development server:

```bash
python main.py
# or
uvicorn app.main:app --reload
```

4. Open http://127.0.0.1:8000 in your browser.

## How to Play

1. From Home, click "Create Game".
2. Choose player count (2–4) and your name; submit.
3. You will land on the configuration page. Share the invite link with friends.
4. Each player selects a ship and upgrades within the 100-token budget.
5. In the Lobby, each player toggles Ready. The host starts the game when all are ready.
6. The Game page shows ship dashboards and streams the battle log in real-time.
7. After the battle, you will be redirected to the Game Over screen.

## Pages

- `/` Home + Leaderboard
- `/create` Create Game (GET/POST)
- `/join/{code}` Join Game (GET/POST)
- `/configure?code=ABC123&player_id=1` Configure ship and upgrades (POST submits here)
- `/lobby/{code}` Waiting room (HTMX refreshes player list every second)
- `/game/{code}` Game dashboard w/ live battle log (WebSocket)
- `/game_over/{code}` Summary and winner

## Data Model (simplified)

- ShipType: base stats (health, shields, power, speed, fuel, weapons, cargo capacity, crew) and token cost
- UpgradeType: token cost and stat deltas (health, shields, power, speed, fuel, weapons, cargo capacity)
- Game: code, max players, status (waiting/active/completed), timestamps, winner
- GamePlayer: per-game player with tokens balance, readiness, selected ship, current stats
- PlayerUpgrade: many-to-many between player and upgrades

All schema is created on startup; ships and upgrades are seeded on first run.

## Environment Variables

See `.env.example`:

- `DATABASE_URL` (default: `sqlite:///./pftl.db`)
- `APP_HOST` (default: `127.0.0.1`)
- `APP_PORT` (default: `8000`)
- `DEBUG` (default: `true`)
- `SECRET_KEY` (development default provided; change for production)

For PostgreSQL:

```
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/pftl
```

Install a PostgreSQL driver (e.g., `psycopg[binary]`) if using Postgres.

## Development Notes

- Style: 4 spaces, double quotes, max line length 120, docstrings for public functions/classes.
- Templates are in `app/templates`; HTMX fragments are in `app/templates/fragments`.
- Static (optional) can be placed under `app/static`.

## License

This project is provided as-is for demonstration and educational purposes.
