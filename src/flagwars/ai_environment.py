"""
人机AI规则环境接口
封装游戏状态，提供决策接口给AI使用
"""
import random
from typing import Dict, List, Tuple, Optional, Any
from models import GameState, Player, Tile, TerrainType


class AIEnvironment:
    """AI决策环境类，封装游戏状态并提供决策接口"""

    def __init__(self, game_state: GameState, ai_player_id: int):
        """
        初始化AI环境

        Args:
            game_state: 游戏状态对象
            ai_player_id: AI控制的玩家ID
        """
        self.game_state = game_state
        self.ai_player_id = ai_player_id
        self.ai_player = self._get_ai_player()

        # 决策历史（用于调试和学习）
        self.decision_history = []

    def _get_ai_player(self) -> Optional[Player]:
        """获取AI玩家对象"""
        return self.game_state.players.get(self.ai_player_id)

    def is_game_over(self) -> bool:
        """检查游戏是否结束"""
        return self.game_state.game_over

    def is_ai_alive(self) -> bool:
        """检查AI玩家是否存活"""
        return self.ai_player is not None and self.ai_player.is_alive

    def get_visible_tiles(self) -> List[Tile]:
        """获取AI玩家可见的所有地块"""
        visible_tiles = []
        for row in self.game_state.tiles:
            for tile in row:
                if tile.visibility.get(self.ai_player_id, False):
                    visible_tiles.append(tile)
        return visible_tiles

    def get_owned_tiles(self) -> List[Tile]:
        """获取AI玩家拥有的所有地块"""
        owned_tiles = []
        for row in self.game_state.tiles:
            for tile in row:
                if tile.owner and tile.owner.id == self.ai_player_id:
                    owned_tiles.append(tile)
        return owned_tiles

    def get_enemy_tiles(self) -> List[Tile]:
        """获取AI玩家可见的敌方地块"""
        enemy_tiles = []
        for row in self.game_state.tiles:
            for tile in row:
                if (tile.visibility.get(self.ai_player_id, False) and
                        tile.owner and tile.owner.id != self.ai_player_id):
                    enemy_tiles.append(tile)
        return enemy_tiles

    def get_neutral_tiles(self) -> List[Tile]:
        """获取AI玩家可见的中立地块"""
        neutral_tiles = []
        for row in self.game_state.tiles:
            for tile in row:
                if (tile.visibility.get(self.ai_player_id, False) and
                        tile.owner is None and tile.can_be_captured()):
                    neutral_tiles.append(tile)
        return neutral_tiles

    def get_player_stats(self) -> Dict[str, Any]:
        """获取AI玩家的统计数据"""
        return self.game_state.get_player_stats(self.ai_player_id)

    def get_all_players_stats(self) -> List[Dict]:
        """获取所有玩家的统计数据"""
        return self.game_state.get_all_players_stats()

    def get_tile_at(self, x: int, y: int) -> Optional[Tile]:
        """获取指定坐标的地块（如果可见）"""
        if not (0 <= x < self.game_state.map_width and 0 <= y < self.game_state.map_height):
            return None

        tile = self.game_state.tiles[y][x]
        if tile.visibility.get(self.ai_player_id, False):
            return tile
        return None

    def get_adjacent_tiles(self, tile: Tile) -> List[Tuple[Tile, str]]:
        """
        获取相邻地块和方向

        Returns:
            List[(Tile, direction)] - 方向: 'up', 'down', 'left', 'right'
        """
        directions = []
        x, y = tile.x, tile.y

        # 上
        if y > 0:
            adj_tile = self.game_state.tiles[y - 1][x]
            if adj_tile.visibility.get(self.ai_player_id, False):
                directions.append((adj_tile, 'up'))

        # 下
        if y < self.game_state.map_height - 1:
            adj_tile = self.game_state.tiles[y + 1][x]
            if adj_tile.visibility.get(self.ai_player_id, False):
                directions.append((adj_tile, 'down'))

        # 左
        if x > 0:
            adj_tile = self.game_state.tiles[y][x - 1]
            if adj_tile.visibility.get(self.ai_player_id, False):
                directions.append((adj_tile, 'left'))

        # 右
        if x < self.game_state.map_width - 1:
            adj_tile = self.game_state.tiles[y][x + 1]
            if adj_tile.visibility.get(self.ai_player_id, False):
                directions.append((adj_tile, 'right'))

        return directions

    def get_possible_moves_from_tile(self, tile: Tile) -> List[Tuple[int, int]]:
        """
        获取从指定地块可以移动到的所有位置

        Returns:
            List[(to_x, to_y)]
        """
        if not tile.owner or tile.owner.id != self.ai_player_id:
            return []

        if tile.soldiers <= 1:
            return []

        possible_moves = []
        x, y = tile.x, tile.y

        # 检查四个方向
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < self.game_state.map_width and
                    0 <= ny < self.game_state.map_height):

                target_tile = self.game_state.tiles[ny][nx]
                # 只需要知道是否可通行，战争迷雾不影响移动合法性
                if target_tile.is_passable():
                    possible_moves.append((nx, ny))

        return possible_moves

    def evaluate_move(self, from_x: int, from_y: int, to_x: int, to_y: int) -> Dict[str, Any]:
        """
        评估移动的潜在效果（模拟计算，不实际执行）

        Returns:
            包含评估结果的字典
        """
        result = {
            'valid': False,
            'risk_level': 0,  # 0-10，越高风险越大
            'potential_gain': 0,  # 预期获得的兵力或地块价值
            'move_type': None,  # 'reinforce', 'attack', 'capture'
            'success_probability': 0.0  # 成功概率估计
        }

        # 验证基本合法性
        if not (0 <= from_x < self.game_state.map_width and
                0 <= from_y < self.game_state.map_height):
            return result

        if not (0 <= to_x < self.game_state.map_width and
                0 <= to_y < self.game_state.map_height):
            return result

        from_tile = self.game_state.tiles[from_y][from_x]
        to_tile = self.game_state.tiles[to_y][to_x]

        # 检查所有权和可通行性
        if not from_tile.owner or from_tile.owner.id != self.ai_player_id:
            return result

        if not to_tile.is_passable():
            return result

        if from_tile.soldiers <= 1:
            return result

        result['valid'] = True

        # 计算可移动的士兵数量
        movable_soldiers = from_tile.soldiers - 1

        # 判断移动类型
        if to_tile.owner is None:
            result['move_type'] = 'capture'
            # 占领中立地块
            if movable_soldiers > to_tile.soldiers:
                result['success_probability'] = 1.0
                result['potential_gain'] = 1  # 获得一个地块
            elif movable_soldiers == to_tile.soldiers:
                result['success_probability'] = 0.5  # 同归于尽
                result['risk_level'] = 5
            else:
                result['success_probability'] = 0.0
                result['risk_level'] = 8

        elif to_tile.owner.id == self.ai_player_id:
            result['move_type'] = 'reinforce'
            result['success_probability'] = 1.0
            result['risk_level'] = 0

        else:
            result['move_type'] = 'attack'
            # 攻击敌方地块
            if movable_soldiers > to_tile.soldiers:
                result['success_probability'] = 0.8  # 考虑可能的反击
                result['potential_gain'] = to_tile.soldiers + 1  # 获得敌方兵力
                result['risk_level'] = 3
            elif movable_soldiers == to_tile.soldiers:
                result['success_probability'] = 0.5
                result['risk_level'] = 6
            else:
                result['success_probability'] = 0.2
                result['risk_level'] = 9

        return result

    def execute_move(self, from_x: int, from_y: int, to_x: int, to_y: int) -> bool:
        """
        执行移动操作

        Returns:
            是否成功执行
        """
        success = self.game_state.move_soldiers(from_x, from_y, to_x, to_y, self.ai_player_id)

        if success:
            # 记录决策历史
            self.decision_history.append({
                'tick': self.game_state.current_tick,
                'from': (from_x, from_y),
                'to': (to_x, to_y),
                'action': 'move'
            })

        return success

    def get_defensive_priority(self, tile: Tile) -> float:
        """
        计算地块的防御优先级

        Returns:
            优先级分数（越高越需要防守）
        """
        priority = 0.0

        # 基地最高优先级
        if tile.terrain_type == TerrainType.BASE:
            priority += 100

        # 塔楼高优先级
        if tile.terrain_type == TerrainType.TOWER:
            priority += 30

        # 士兵数量越多越重要
        priority += tile.soldiers * 0.1

        # 检查相邻的敌方威胁
        adj_tiles = self.get_adjacent_tiles(tile)
        for adj_tile, _ in adj_tiles:
            if adj_tile.owner and adj_tile.owner.id != self.ai_player_id:
                # 敌方相邻，提高防御优先级
                priority += adj_tile.soldiers * 0.5

        return priority

    def get_attack_priority(self, target_tile: Tile) -> float:
        """
        计算攻击目标的优先级

        Returns:
            优先级分数（越高越值得攻击）
        """
        priority = 0.0

        # 敌方基地最高优先级
        if target_tile.terrain_type == TerrainType.BASE:
            priority += 200

        # 敌方塔楼高优先级
        if target_tile.terrain_type == TerrainType.TOWER:
            priority += 50

        # 兵力较少的敌人更容易攻击
        if target_tile.owner:
            priority += max(0, 20 - target_tile.soldiers) * 2

        # 中立地块优先级较低
        if target_tile.owner is None:
            priority += 10

        # 考虑地形价值
        if target_tile.terrain_type == TerrainType.PLAIN:
            priority += 5
        elif target_tile.terrain_type == TerrainType.SWAMP:
            priority -= 5  # 沼泽有负面影响

        return priority

    def suggest_strategic_move(self) -> Optional[Dict[str, Any]]:
        """
        建议一个战略性移动（基于规则的AI决策）

        Returns:
            建议的移动信息或None
        """
        owned_tiles = self.get_owned_tiles()

        if not owned_tiles:
            return None

        # 策略1：优先防守重要地块
        defensive_tiles = sorted(owned_tiles,
                                 key=lambda t: self.get_defensive_priority(t),
                                 reverse=True)[:5]

        # 策略2：寻找攻击目标
        visible_enemy_tiles = self.get_enemy_tiles()
        visible_neutral_tiles = self.get_neutral_tiles()

        attack_targets = []
        for tile in visible_enemy_tiles + visible_neutral_tiles:
            priority = self.get_attack_priority(tile)
            attack_targets.append((tile, priority))

        attack_targets.sort(key=lambda x: x[1], reverse=True)

        # 尝试为每个防守地块找到安全的移动
        for defense_tile in defensive_tiles:
            # 如果防守地块兵力充足，可以考虑向外扩张
            if defense_tile.soldiers > 5:
                possible_moves = self.get_possible_moves_from_tile(defense_tile)

                for tx, ty in possible_moves:
                    target_tile = self.game_state.tiles[ty][tx]

                    # 评估移动
                    evaluation = self.evaluate_move(
                        defense_tile.x, defense_tile.y, tx, ty
                    )

                    if evaluation['valid'] and evaluation['success_probability'] > 0.6:
                        # 找到合适的移动
                        return {
                            'from_x': defense_tile.x,
                            'from_y': defense_tile.y,
                            'to_x': tx,
                            'to_y': ty,
                            'evaluation': evaluation
                        }

        # 如果防守策略没有找到合适移动，尝试攻击策略
        if attack_targets:
            best_target, _ = attack_targets[0]

            # 寻找最近的己方地块攻击该目标
            for owned_tile in owned_tiles:
                if owned_tile.soldiers > 3:
                    # 检查是否相邻
                    if (abs(owned_tile.x - best_target.x) +
                        abs(owned_tile.y - best_target.y)) == 1:

                        evaluation = self.evaluate_move(
                            owned_tile.x, owned_tile.y,
                            best_target.x, best_target.y
                        )

                        if evaluation['valid'] and evaluation['success_probability'] > 0.4:
                            return {
                                'from_x': owned_tile.x,
                                'from_y': owned_tile.y,
                                'to_x': best_target.x,
                                'to_y': best_target.y,
                                'evaluation': evaluation
                            }

        return None

    def make_ai_decision(self) -> bool:
        """
        AI自动决策（调用建议策略并执行）

        Returns:
            是否成功执行了决策
        """
        if not self.is_ai_alive() or self.is_game_over():
            return False

        suggested_move = self.suggest_strategic_move()

        if suggested_move:
            return self.execute_move(
                suggested_move['from_x'],
                suggested_move['from_y'],
                suggested_move['to_x'],
                suggested_move['to_y']
            )

        return False