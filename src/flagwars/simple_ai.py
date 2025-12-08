"""
简单规则AI示例
"""
import random
from typing import List, Tuple, Optional
from ai_environment import AIEnvironment
from models import GameState, Player, Tile


class SimpleAI:
    """简单规则AI"""

    def __init__(self, player_id: int, aggression: float = 0.7):
        """
        Args:
            player_id: AI控制的玩家ID
            aggression: 攻击性系数 (0.0-1.0)
        """
        self.player_id = player_id
        self.aggression = aggression
        self.environment = None

    def connect_to_game(self, game_state: GameState):
        """连接到游戏状态"""
        self.environment = AIEnvironment(game_state, self.player_id)

    def decide_and_act(self) -> bool:
        """做出决策并执行动作"""
        if not self.environment:
            return False

        # 获取当前状态
        owned_tiles = self.environment.get_owned_tiles()
        visible_enemies = self.environment.get_enemy_tiles()
        visible_neutrals = self.environment.get_neutral_tiles()

        # 决策逻辑
        if random.random() < self.aggression and visible_enemies:
            # 攻击模式
            return self._attack_decision()
        else:
            # 扩张模式
            return self._expand_decision()

    def _attack_decision(self) -> bool:
        """攻击决策"""
        owned_tiles = self.environment.get_owned_tiles()
        enemy_tiles = self.environment.get_enemy_tiles()

        if not owned_tiles or not enemy_tiles:
            return False

        # 寻找兵力最强的己方地块
        strong_tile = max(owned_tiles, key=lambda t: t.soldiers)

        if strong_tile.soldiers <= 1:
            return False

        # 寻找最近的敌方目标
        enemy_tiles.sort(key=lambda t: abs(t.x - strong_tile.x) + abs(t.y - strong_tile.y))

        for enemy in enemy_tiles[:3]:  # 检查最近的3个敌人
            # 检查是否相邻
            if (abs(strong_tile.x - enemy.x) + abs(strong_tile.y - enemy.y)) == 1:
                return self.environment.execute_move(
                    strong_tile.x, strong_tile.y,
                    enemy.x, enemy.y
                )

        return False

    def _expand_decision(self) -> bool:
        """扩张决策"""
        owned_tiles = self.environment.get_owned_tiles()
        neutral_tiles = self.environment.get_neutral_tiles()

        if not owned_tiles:
            return False

        # 随机选择一个己方地块
        source_tile = random.choice(owned_tiles)

        if source_tile.soldiers <= 1:
            return False

        # 寻找相邻的中立地块
        adjacent = self.environment.get_adjacent_tiles(source_tile)

        for adj_tile, direction in adjacent:
            if adj_tile.owner is None and adj_tile.can_be_captured():
                return self.environment.execute_move(
                    source_tile.x, source_tile.y,
                    adj_tile.x, adj_tile.y
                )

        return False

    def get_stats(self) -> dict:
        """获取AI统计信息"""
        if self.environment:
            return self.environment.get_player_stats()
        return {}