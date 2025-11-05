# FlagWars
> May the FLAG be with you.

## License
This project is licensed under the [GNU GPLv3 License](LICENSE).

FlagWars is a modern *Capture the Flag* game. In this game, each player has a base. The goal of the game is to capture the opponents' bases and become the last player with a base.

## Terrain Types
There are various terrain types in the game, including:

1. **Plains**: Plains are the most basic terrain type. They are flat and passable. Each plain tile you occupy will generate one soldier every 15 game ticks.

2. **Base**: The base is the player's home. It is passable and generates one soldier every game tick. If a player's base is captured, that player loses the game.

3. **Tower**: Towers are passable terrain. Capturing a tower requires a specific number of soldiers. If a player occupies a tower, the tower will generate one soldier every game tick like a base. Towers are randomly generated naturally in the game.

4. **Wall**: Walls are impassable terrain. They can be destroyed by a specific number of soldiers. Walls are randomly generated naturally in the game.

5. **Mountain**: Mountains are impassable terrain. They are randomly generated naturally in the game. Unlike walls, mountains cannot be destroyed.

6. **Swamp**: Swamps are passable terrain. They are randomly generated naturally in the game. Swamps reduce soldiers standing on them by one soldier per game tick.

## Gameplay
Players can use the mouse pointer to select their soldiers. Selected soldiers will be highlighted. Use arrow keys to plan soldier movement.

When a player's soldiers step on a tile, that tile is occupied. Soldiers from multiple players on the same tile will cancel each other out. Certain terrain types, such as walls and towers, will cancel soldiers on the tile and reduce the number of soldiers needed for occupation until fully captured.

The game ends when all players except one have lost their bases.

Attack, defend, cooperate, and betray... use every opportunity to win!

# Tech Stack

- **Server**: Python + Tornado (WebSocket communication)
- **Client**: HTML5 Canvas + Brython (Python in Browser)
- **Package Management**: uv (modern Python package manager)

