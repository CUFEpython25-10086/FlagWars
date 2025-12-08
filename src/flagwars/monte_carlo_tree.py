"""
蒙特卡洛树搜索实现
"""
import numpy as np
import math
import random
from typing import List, Dict, Any, Optional, Tuple
from mcts_environment import MCTSGameEnvironment
from neural_network import GameCNN


class Node:
    """MCTS节点"""

    def __init__(self, prior: float, parent: Optional['Node'] = None):
        self.parent = parent
        self.children: Dict[int, Node] = {}

        self.visit_count = 0
        self.value_sum = 0.0
        self.prior = prior
        self.state = None  # 游戏状态（延迟加载）

    def expanded(self) -> bool:
        """是否已扩展"""
        return len(self.children) > 0

    def value(self) -> float:
        """节点价值"""
        if self.visit_count == 0:
            return 0.0
        return self.value_sum / self.visit_count

    def ucb_score(self, parent_visit: int, c_puct: float = 1.0) -> float:
        """计算UCB分数"""
        if self.visit_count == 0:
            q_value = 0.0
        else:
            q_value = self.value()

        # 探索项
        u_value = c_puct * self.prior * math.sqrt(parent_visit) / (1 + self.visit_count)

        return q_value + u_value

    def select_child(self, c_puct: float = 1.0) -> Tuple[int, 'Node']:
        """选择子节点"""
        best_score = -float('inf')
        best_action = -1
        best_child = None

        for action, child in self.children.items():
            score = child.ucb_score(self.visit_count, c_puct)
            if score > best_score:
                best_score = score
                best_action = action
                best_child = child

        return best_action, best_child

    def expand(self, action_probs: np.ndarray, valid_actions: np.ndarray):
        """扩展节点"""
        # 只扩展有效动作
        for action_idx, prob in enumerate(action_probs):
            if valid_actions[action_idx] > 0.5:  # 有效动作
                self.children[action_idx] = Node(prior=prob, parent=self)


class MCTS:
    """蒙特卡洛树搜索"""

    def __init__(self, model: GameCNN, num_simulations: int = 800,
                 c_puct: float = 1.0, temperature: float = 1.0):
        self.model = model
        self.num_simulations = num_simulations
        self.c_puct = c_puct
        self.temperature = temperature

    def search(self, env: MCTSGameEnvironment, device=None) -> np.ndarray:
        """
        执行MCTS搜索

        Returns:
            动作概率分布
        """
        root = Node(prior=0.0)

        for _ in range(self.num_simulations):
            node = root
            search_path = [node]
            current_env = env.clone()

            # 选择阶段
            while node.expanded():
                action, node = node.select_child(self.c_puct)
                search_path.append(node)
                current_env, _, _ = current_env.take_action(action)

            # 扩展和评估阶段
            if not current_env.is_terminal():
                # 获取神经网络预测
                state = current_env.get_state_representation()
                action_probs, value = self.model.predict(state, device)

                # 获取有效动作掩码
                valid_actions = current_env.get_valid_actions()

                # 掩码无效动作
                action_probs = action_probs * valid_actions
                if np.sum(action_probs) > 0:
                    action_probs /= np.sum(action_probs)  # 重新归一化
                else:
                    # 如果没有有效动作，均匀分布
                    action_probs = valid_actions / np.sum(valid_actions)

                # 扩展节点
                node.expand(action_probs, valid_actions)
            else:
                # 终止状态，使用游戏结果
                value = current_env.get_result()

            # 回传阶段
            self._backpropagate(search_path, value, current_env.get_current_player())

        # 根据访问计数计算策略
        visit_counts = np.zeros(env.action_space_size)
        for action, child in root.children.items():
            visit_counts[action] = child.visit_count

        # 应用温度参数
        if self.temperature == 0:
            # 贪婪选择
            action = np.argmax(visit_counts)
            probs = np.zeros_like(visit_counts)
            probs[action] = 1.0
        else:
            # 温度采样
            visit_counts = visit_counts ** (1.0 / self.temperature)
            probs = visit_counts / np.sum(visit_counts)

        return probs

    def _backpropagate(self, search_path: List[Node], value: float, player: int):
        """回传价值"""
        # 从对手视角翻转价值
        for node in reversed(search_path):
            node.value_sum += value if (len(search_path) - search_path.index(node)) % 2 == 0 else -value
            node.visit_count += 1

    def get_action(self, env: MCTSGameEnvironment, device=None, deterministic: bool = False) -> int:
        """
        获取动作

        Args:
            deterministic: 是否使用确定性策略
        """
        if deterministic:
            self.temperature = 0
        else:
            self.temperature = 1.0

        probs = self.search(env, device)

        if deterministic:
            return np.argmax(probs)
        else:
            return np.random.choice(len(probs), p=probs)
        