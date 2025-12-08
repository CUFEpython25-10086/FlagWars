"""
MCTS专用的游戏环境包装
提供神经网络友好的状态表示和动作空间
"""
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from models import GameState, Player, Tile, TerrainType


class MCTSGameEnvironment:
    """MCTS专用的游戏环境"""

    def __init__(self, game_state: GameState, player_id: int):
        self.game_state = game_state
        self.player_id = player_id
        self.player = game_state.players.get(player_id)

        # 动作空间维度 (20x20x4 = 上/下/左/右)
        self.action_space_size = 20 * 20 * 4

    def get_current_player(self) -> int:
        """获取当前玩家ID"""
        return self.player_id

    def get_valid_actions(self) -> np.ndarray:
        """
        获取有效动作的掩码 (20x20x4)

        动作编码: (x, y, direction)
        direction: 0=上, 1=下, 2=左, 3=右
        """
        valid_actions = np.zeros((20, 20, 4), dtype=np.float32)

        for y in range(20):
            for x in range(20):
                tile = self.game_state.tiles[y][x]

                # 只有己方地块且士兵数量>1才能移动
                if (tile.owner and tile.owner.id == self.player_id and
                        tile.soldiers > 1):

                    # 检查四个方向
                    for dir_idx, (dx, dy) in enumerate([(0, -1), (0, 1), (-1, 0), (1, 0)]):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < 20 and 0 <= ny < 20:
                            target_tile = self.game_state.tiles[ny][nx]
                            if target_tile.is_passable():
                                valid_actions[y, x, dir_idx] = 1.0

        return valid_actions.flatten()

    def get_state_representation(self) -> np.ndarray:
        """
        获取神经网络输入状态 (多通道特征图)

        通道说明:
        0: 己方士兵密度
        1: 敌方士兵密度
        2: 中立士兵密度
        3: 地形类型 (one-hot编码的一部分)
        4: 己方所有权 (0/1)
        5: 敌方所有权 (0/1)
        6: 基地位置 (己方/敌方/无)
        7: 塔楼位置
        8: 战争迷雾 (0=可见, 1=不可见)

        总通道数: 9
        形状: (9, 20, 20)
        """
        state = np.zeros((9, 20, 20), dtype=np.float32)

        for y in range(20):
            for x in range(20):
                tile = self.game_state.tiles[y][x]

                # 通道0-2: 士兵密度
                if tile.owner:
                    if tile.owner.id == self.player_id:
                        # 己方士兵 (归一化到0-1)
                        state[0, y, x] = min(tile.soldiers / 50.0, 1.0)
                    else:
                        # 敌方士兵
                        state[1, y, x] = min(tile.soldiers / 50.0, 1.0)
                else:
                    # 中立士兵
                    state[2, y, x] = min(tile.soldiers / 20.0, 1.0)

                # 通道3-6: 地形和所有权
                if tile.terrain_type == TerrainType.BASE:
                    state[3, y, x] = 1.0
                    if tile.owner:
                        if tile.owner.id == self.player_id:
                            state[6, y, x] = 1.0  # 己方基地
                        else:
                            state[6, y, x] = -1.0  # 敌方基地
                elif tile.terrain_type == TerrainType.TOWER:
                    state[4, y, x] = 1.0
                    state[7, y, x] = 1.0
                elif tile.terrain_type == TerrainType.WALL:
                    state[4, y, x] = 1.0
                elif tile.terrain_type == TerrainType.MOUNTAIN:
                    state[5, y, x] = 1.0
                elif tile.terrain_type == TerrainType.SWAMP:
                    state[5, y, x] = 1.0
                else:  # PLAIN
                    state[4, y, x] = 1.0

                # 通道7: 所有权
                if tile.owner:
                    if tile.owner.id == self.player_id:
                        state[7, y, x] = 1.0
                    else:
                        state[7, y, x] = -1.0

                # 通道8: 战争迷雾 (0=可见, 1=不可见)
                if not tile.visibility.get(self.player_id, False):
                    state[8, y, x] = 1.0

        return state

    def take_action(self, action_idx: int) -> Tuple['MCTSGameEnvironment', float, bool]:
        """
        执行动作并返回新环境

        Args:
            action_idx: 扁平化的动作索引 (0-1599)

        Returns:
            (new_env, reward, done)
        """
        # 解码动作
        total_idx = action_idx
        dir_idx = total_idx % 4
        xy_idx = total_idx // 4
        x = xy_idx % 20
        y = xy_idx // 20

        # 方向映射
        direction_map = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        dx, dy = direction_map[dir_idx]
        to_x, to_y = x + dx, y + dy

        # 执行移动
        success = self.game_state.move_soldiers(x, y, to_x, to_y, self.player_id)

        # 计算即时奖励
        reward = 0.0
        if success:
            # 移动成功的基础奖励
            reward += 0.01

            # 如果攻击成功，额外奖励
            target_tile = self.game_state.tiles[to_y][to_x]
            if target_tile.owner and target_tile.owner.id != self.player_id:
                # 攻击敌方
                reward += 0.1

        # 检查游戏是否结束
        done = self.game_state.game_over

        # 创建新环境实例（相同游戏状态，因为状态已更新）
        new_env = MCTSGameEnvironment(self.game_state, self.player_id)

        return new_env, reward, done

    def is_terminal(self) -> bool:
        """检查是否为终止状态"""
        return self.game_state.game_over

    def get_result(self) -> float:
        """
        获取游戏结果（从当前玩家视角）

        Returns:
            1.0: 当前玩家胜利
            -1.0: 当前玩家失败
            0.0: 平局或未结束
        """
        if not self.game_state.game_over:
            return 0.0

        if self.game_state.winner:
            if self.game_state.winner.id == self.player_id:
                return 1.0
            else:
                return -1.0
        return 0.0  # 平局

    def get_symmetries(self, pi: np.ndarray) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        获取状态的对称变换（用于数据增强）

        Returns:
            List of (state, policy) pairs
        """
        symmetries = []

        # 原始状态
        state = self.get_state_representation()
        pi_matrix = pi.reshape(20, 20, 4)

        # 旋转90度 (3次)
        for k in range(1, 4):
            # 旋转状态
            rotated_state = np.rot90(state, k=k, axes=(1, 2))
            # 旋转策略
            rotated_pi = np.rot90(pi_matrix, k=k, axes=(0, 1))
            # 方向也需要重新映射
            # 方向映射: 旋转时方向也会变化
            # 实现略复杂，这里简化处理
            symmetries.append((rotated_state, rotated_pi.flatten()))

        # 水平翻转
        flipped_state = np.flip(state, axis=2)  # 沿x轴翻转
        flipped_pi = np.flip(pi_matrix, axis=1)  # 沿x轴翻转
        # 需要调整左右方向
        temp = flipped_pi[:, :, 2].copy()
        flipped_pi[:, :, 2] = flipped_pi[:, :, 3]
        flipped_pi[:, :, 3] = temp
        symmetries.append((flipped_state, flipped_pi.flatten()))

        return symmetries

    def clone(self) -> 'MCTSGameEnvironment':
        """创建环境的深拷贝"""
        # 需要实现GameState的深拷贝
        # 这里简化处理，实际使用时需要完整实现
        import copy
        cloned_state = copy.deepcopy(self.game_state)
        return MCTSGameEnvironment(cloned_state, self.player_id)