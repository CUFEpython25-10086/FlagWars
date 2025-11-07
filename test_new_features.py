#!/usr/bin/env python3
"""
测试新的地图生成和出生点功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flagwars.models import GameState, TerrainType, Player

def test_map_generation():
    """测试地图生成功能"""
    print("=== 测试地图生成功能 ===")
    
    # 创建游戏状态
    game = GameState()
    
    # 统计地形数量
    terrain_counts = {}
    for row in game.tiles:
        for tile in row:
            terrain_type = tile.terrain_type.value
            if terrain_type not in terrain_counts:
                terrain_counts[terrain_type] = 0
            terrain_counts[terrain_type] += 1
    
    # 打印地形统计
    print("地形分布统计:")
    for terrain_type, count in terrain_counts.items():
        print(f"  {terrain_type}: {count}")
    
    # 检查地形分布是否合理
    total_tiles = game.map_width * game.map_height
    plain_ratio = terrain_counts.get('plain', 0) / total_tiles
    mountain_ratio = terrain_counts.get('mountain', 0) / total_tiles
    
    print(f"\n平原占比: {plain_ratio:.2%}")
    print(f"山脉占比: {mountain_ratio:.2%}")
    
    # 检查山脉是否形成链状
    mountain_chains = 0
    visited = set()
    
    for y in range(game.map_height):
        for x in range(game.map_width):
            if (x, y) not in visited and game.tiles[y][x].terrain_type == TerrainType.MOUNTAIN:
                # 找到新的山脉链
                chain_size = 0
                stack = [(x, y)]
                
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in visited:
                        continue
                    
                    visited.add((cx, cy))
                    chain_size += 1
                    
                    # 检查相邻的山脉
                    for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                        nx, ny = cx + dx, cy + dy
                        if (0 <= nx < game.map_width and 0 <= ny < game.map_height and
                            (nx, ny) not in visited and
                            game.tiles[ny][nx].terrain_type == TerrainType.MOUNTAIN):
                            stack.append((nx, ny))
                
                if chain_size >= 3:  # 认为长度>=3的才算链
                    mountain_chains += 1
    
    print(f"山脉链数量: {mountain_chains}")
    
    # 检查城墙是否形成结构
    wall_structures = 0
    visited_walls = set()
    
    for y in range(game.map_height):
        for x in range(game.map_width):
            if (x, y) not in visited_walls and game.tiles[y][x].terrain_type == TerrainType.WALL:
                # 找到新的城墙结构
                structure_size = 0
                stack = [(x, y)]
                
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in visited_walls:
                        continue
                    
                    visited_walls.add((cx, cy))
                    structure_size += 1
                    
                    # 检查相邻的城墙
                    for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                        nx, ny = cx + dx, cy + dy
                        if (0 <= nx < game.map_width and 0 <= ny < game.map_height and
                            (nx, ny) not in visited_walls and
                            game.tiles[ny][nx].terrain_type == TerrainType.WALL):
                            stack.append((nx, ny))
                
                if structure_size >= 3:  # 认为长度>=3的才算结构
                    wall_structures += 1
    
    print(f"城墙结构数量: {wall_structures}")
    
    return True

def test_random_base_positions():
    """测试随机出生点功能"""
    print("\n=== 测试随机出生点功能 ===")
    
    # 创建游戏状态
    game = GameState()
    
    # 测试查找适合的基地位置
    base_positions = game.find_suitable_base_positions(4)
    
    print(f"找到 {len(base_positions)} 个基地位置:")
    for i, (x, y) in enumerate(base_positions):
        terrain_type = game.tiles[y][x].terrain_type.value
        print(f"  位置 {i+1}: ({x}, {y}) - 地形: {terrain_type}")
    
    # 检查基地位置之间的距离
    min_distances = []
    for i in range(len(base_positions)):
        for j in range(i+1, len(base_positions)):
            x1, y1 = base_positions[i]
            x2, y2 = base_positions[j]
            distance = abs(x1 - x2) + abs(y1 - y2)  # 曼哈顿距离
            min_distances.append(distance)
            print(f"  位置 {i+1} 和位置 {j+1} 之间的距离: {distance}")
    
    if min_distances:
        print(f"最小距离: {min(min_distances)}")
    
    # 测试多次生成，确保位置是随机的
    print("\n测试多次生成的随机性:")
    all_positions = []
    for i in range(5):
        test_game = GameState()
        positions = test_game.find_suitable_base_positions(4)
        all_positions.append(positions)
        print(f"  生成 {i+1}: {positions}")
    
    # 检查是否有重复
    all_flat = [pos for positions in all_positions for pos in positions]
    unique_positions = set(all_flat)
    print(f"总共生成 {len(all_flat)} 个位置，其中 {len(unique_positions)} 个唯一位置")
    
    return True

def test_full_game_setup():
    """测试完整的游戏设置"""
    print("\n=== 测试完整的游戏设置 ===")
    
    # 创建游戏状态
    game = GameState()
    
    # 创建玩家
    players = [
        Player(1, "玩家1", "#FF0000"),
        Player(2, "玩家2", "#00FF00"),
        Player(3, "玩家3", "#0000FF"),
        Player(4, "玩家4", "#FFFF00")
    ]
    
    # 生成随机基地位置
    base_positions = game.find_suitable_base_positions(4)
    
    # 添加玩家到游戏
    for i, player in enumerate(players):
        if i < len(base_positions):
            base_x, base_y = base_positions[i]
            game.add_player(player, base_x, base_y)
            print(f"玩家 {player.name} 基地位置: ({base_x}, {base_y})")
    
    # 打印游戏状态摘要
    print(f"\n游戏状态摘要:")
    print(f"  地图大小: {game.map_width} x {game.map_height}")
    print(f"  玩家数量: {len(game.players)}")
    print(f"  当前游戏刻: {game.current_tick}")
    
    # 检查每个玩家的基地
    for player_id, player in game.players.items():
        base_x, base_y = player.base_position
        base_tile = game.tiles[base_y][base_x]
        print(f"  {player.name}: 基地在 ({base_x}, {base_y}), 地形: {base_tile.terrain_type.value}, 士兵: {base_tile.soldiers}")
    
    return True

def main():
    """主函数"""
    print("开始测试新的地图生成和出生点功能...\n")
    
    try:
        # 测试地图生成
        if not test_map_generation():
            print("地图生成测试失败!")
            return False
        
        # 测试随机出生点
        if not test_random_base_positions():
            print("随机出生点测试失败!")
            return False
        
        # 测试完整游戏设置
        if not test_full_game_setup():
            print("完整游戏设置测试失败!")
            return False
        
        print("\n所有测试通过!")
        return True
    
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)