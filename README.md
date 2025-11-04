# FlagWars
> May the FLAG be with you.

FlagWars is a modern *Capture the Flag* game. In this game, each player has a BASE. The objective is to capture opponents' bases and become the last player standing with a base.

## Terrain Types
There are several types of terrain in the game, including:

1. **Plain**: The most basic terrain type. It is flat and walkable. Each plain tile you occupy will generate one soldier every 15 ticks.

2. **Base**: The player's home territory. It is walkable and generates one soldier every tick. If a player's base is captured, that player loses the game.

3. **Tower**: A walkable terrain that requires a specific number of soldiers to conquer. Once conquered, the tower generates one soldier every tick, similar to a base. Towers are formed naturally and randomly throughout the game.

4. **Wall**: A non-walkable terrain that can be destroyed by a specific number of soldiers. Walls are formed naturally and randomly in the game.

5. **Mountain**: A non-walkable terrain that is formed naturally and randomly. Unlike walls, mountains cannot be destroyed.

6. **Swamp**: A walkable terrain that is formed naturally and randomly. Swamps reduce the number of soldiers standing on them by one every tick.

## Gameplay
Players can use the mouse pointer to select their soldiers. Selected soldiers will be highlighted. Use the arrow keys to plan and execute movements.

A tile is conquered when a player's soldier steps on it. Multiple players' soldiers on the same tile will cancel each other out. Certain terrain types, such as walls and towers, will neutralize soldiers on the tile and reduce the required number of soldiers needed to conquer the tile until it is fully captured.

The game ends when all players except one have lost their bases.

Attack, Defense, Cooperation, and Betrayal... Use every opportunity to win!

## Tech Stack
Developed with Python
Server: Tornado
Client: Brython + HTML5 Canvas
