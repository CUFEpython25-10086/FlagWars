#!/usr/bin/env python
"""测试地形生成和玩家基地位置功能"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from flagwars.models import GameState, Player, TerrainType

def test_terrain_generation():
    """测试地形生成功能"""
    print("=== 测试地形生成功能 ===")
    
    # 创建游戏状态
    game_state = GameState(map_width=20, map_height=15)
    
    # 统计各种地形类型的数量
    terrain_counts = {}
    for terrain_type in TerrainType:
        terrain_counts[terrain_type.value] = 0
    
    # 遍历地图统计地形
    for row in game_state.tiles:
        for tile in row:
            terrain_counts[tile.terrain_type.value] += 1
    
    # 打印统计结果
    print("地形统计:")
    for terrain_type, count in terrain_counts.items():
        print(f"  {terrain_type}: {count}")
    
    # 验证地形数量是否合理
    assert terrain_counts["plain"] > 0, "平原数量应该大于0"
    assert terrain_counts["tower"] == 8, f"塔楼数量应该是8，实际是{terrain_counts['tower']}"
    assert terrain_counts["wall"] == 10, f"城墙数量应该是10，实际是{terrain_counts['wall']}"
    assert terrain_counts["mountain"] == 12, f"山脉数量应该是12，实际是{terrain_counts['mountain']}"
    assert terrain_counts["swamp"] == 6, f"沼泽数量应该是6，实际是{terrain_counts['swamp']}"
    
    print("✓ 地形生成测试通过")
    return True

def test_spawn_points():
    """测试玩家出生点生成功能"""
    print("\n=== 测试玩家出生点生成功能 ===")
    
    # 创建游戏状态
    game_state = GameState(map_width=20, map_height=15)
    
    # 测试不同玩家数量的出生点生成
    for num_players in [2, 4, 6, 8]:
        print(f"测试 {num_players} 个玩家的出生点生成...")
        
        # 生成出生点
        spawn_points = game_state.generate_random_spawn_points(num_players)
        
        # 验证出生点数量
        assert len(spawn_points) == num_players, f"出生点数量应该是{num_players}，实际是{len(spawn_points)}"
        
        # 验证每个出生点都在平原上
        for x, y in spawn_points:
            terrain_type = game_state.tiles[y][x].terrain_type
            assert terrain_type == TerrainType.PLAIN, f"出生点({x},{y})应该在平原上，实际地形是{terrain_type.value}"
        
        # 验证出生点之间的距离
        min_distance = max(min(game_state.map_width, game_state.map_height) // 3, 5)
        for i, (x1, y1) in enumerate(spawn_points):
            for j, (x2, y2) in enumerate(spawn_points):
                if i != j:
                    distance = abs(x1 - x2) + abs(y1 - y2)
                    assert distance >= min_distance, f"出生点({x1},{y1})和({x2},{y2})之间的距离应该至少为{min_distance}，实际是{distance}"
        
        print(f"  ✓ {num_players} 个玩家的出生点生成测试通过")
    
    return True

def test_player_base_placement():
    """测试玩家基地放置功能"""
    print("\n=== 测试玩家基地放置功能 ===")
    
    # 创建游戏状态
    game_state = GameState(map_width=20, map_height=15)
    
    # 生成4个玩家的出生点
    spawn_points = game_state.generate_random_spawn_points(4)
    
    # 创建玩家并放置基地
    players = []
    for i, (x, y) in enumerate(spawn_points):
        player = Player(i+1, f"Player{i+1}", f"#FF00{i}")
        players.append(player)
        game_state.add_player(player, x, y)
        
        # 验证基地是否正确放置
        base_tile = game_state.tiles[y][x]
        assert base_tile.terrain_type == TerrainType.BASE, f"玩家{i+1}的基地地形应该是BASE，实际是{base_tile.terrain_type.value}"
        assert base_tile.owner == player, f"玩家{i+1}的基地所有者应该是玩家{i+1}"
        assert base_tile.soldiers == 10, f"玩家{i+1}的基地士兵数量应该是10，实际是{base_tile.soldiers}"
    
    print("✓ 玩家基地放置测试通过")
    return True

def main():
    """主测试函数"""
    print("开始测试地形生成和玩家基地位置功能...\n")
    
    try:
        # 运行所有测试
        test_terrain_generation()
        test_spawn_points()
        test_player_base_placement()
        
        print("\n🎉 所有测试通过！地形生成和玩家基地位置功能正常工作。")
        return True
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)