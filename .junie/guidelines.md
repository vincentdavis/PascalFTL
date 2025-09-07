# Pascal's Faster Than Light

**A space ship battle simulator between two players.**
## General Features:

- leaderboard
- 2 player mode
- 3 player mode
- 4 player mode
- Multiple ship types
- Multiple add on components for a ship
- Ship dashboard, with stats and upgrades
- ship crew
- ship weapons
- ship upgrades
- ship health
- ship shields
- ship power
- ship speed
- ship fuel
- ship cargo
- ship cargo capacity
- ship cargo space

## Game setup:
How a player can setup a game.
1. A player chooses the number of players 2-4. Then this plaer gets a link to send to each of the other 3 players.(requires a create game page) 
2. Players can choose and configure different ships.

## Pages:
- Home page with leaderboard.
- Create new game, choose number of players, get invites
- Join game, The invite takes you to this page, with the game code.
- Ship selection and configuration page. Player has a number of tokens (money) and can choose from a list of ships and add upgrades.
- Waiting rooom, where players wait for the other players to join.
- Game page, ship dashboard, ship crew, ship weapons, ship upgrades, ship health, ship shields, ship power, ship speed, ship fuel, ship cargo, ship cargo capacity, ship cargo space
- Gome over page, with the winner.

## Space Ship options:
- Battleship
- Destroyer
- Flying Saucers
- Cruiser
- Patrol
- X-Wing
- Y-Wing
- A-Wing
- Millenium Falcon
- TIE Fighter
- TIE Interceptor
- TIE Defender
- TIE Bomber
- TIE Advanced
- TIE Phantom

## Development Environment
- Python 3.13+
- Fastapi backend
- htmx frontend for page updates
- tailwindcss for styling. Dev: `npm run tw:dev` (builds from tailwindcss/styles/app.css to app/static/css/tw.css). Prod: `npm run tw:build`.
- Websockets to stream game updates to the frontend during game play.
- postgresql database for storing game data. (SQLite is used for development)
- Pydantic version 2.0.0+


**Environment Variables**:
   The project uses a `.env` file for development environment variables.

## Code Style and Development Guidelines

### Code Style

2. **Style Guidelines**:
   - Line length: 120 characters
   - Indentation: 4 spaces
   - String quotes: Double quotes
   - Docstrings: Required for all public functions, classes, and methods
   - Also see the `ruff.toml` file.

## Ignore Files
- resources/*.*