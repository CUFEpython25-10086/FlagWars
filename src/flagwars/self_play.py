"""
自对弈数据生成
"""
import numpy as np
import torch
import random
from typing import List, Dict, Any, Tuple
from collections import deque
from models import GameState, Player
from mcts_environment import MCTSGameEnvironment
from monte_carlo_tree import MCTS
from neural_network import GameCNN


class SelfPlayAgent:
    """自对弈代理"""

    def __init__(self, model: GameCNN, device=None,
                 num_simulations: int = 800, temperature_threshold: int = 10):
        self.model = model
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.mcts = MCTS(model, num_simulations=num_simulations)
        self.temperature_threshold = temperature_threshold

    def play_game(self, game_id: int = 0) -> List[Dict[str, Any]]:
        """
        进行一场自对弈

        Returns:
            训练数据列表
        """
        # 创建游戏状态
        game_state = GameState()

        # 创建两个玩家
        player1 = Player(player_id=1, name="AI_Player_1", color="red")
        player2 = Player(player_id=2, name="AI_Player_2", color="blue")

        # 生成出生点
        spawn_points = game_state.generate_random_spawn_points(2)

        # 添加玩家
        game_state.add_player(player1, spawn_points[0][0], spawn_points[0][1])
        game_state.add_player(player2, spawn_points[1][0], spawn_points[1][1])

        # 开始游戏
        game_state.game_started = True

        training_data = []
        move_count = 0

        while not game_state.game_over:
            # 当前玩家
            current_player_id = 1 if move_count % 2 == 0 else 2

            # 创建环境
            env = MCTSGameEnvironment(game_state, current_player_id)

            # 选择温度
            temperature = 1.0 if move_count < self.temperature_threshold else 0.0

            # MCTS搜索
            self.mcts.temperature = temperature
            action_probs = self.mcts.search(env, self.device)

            # 保存训练数据
            state = env.get_state_representation()
            training_data.append({
                'state': state,
                'policy': action_probs,
                'player': current_player_id,
                'move_count': move_count
            })

            # 选择动作
            if temperature > 0:
                action = np.random.choice(len(action_probs), p=action_probs)
            else:
                action = np.argmax(action_probs)

            # 解码并执行动作
            total_idx = action
            dir_idx = total_idx % 4
            xy_idx = total_idx // 4
            x = xy_idx % 20
            y = xy_idx // 20

            direction_map = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            dx, dy = direction_map[dir_idx]
            to_x, to_y = x + dx, y + dy

            # 执行移动
            game_state.move_soldiers(x, y, to_x, to_y, current_player_id)

            # 更新游戏状态
            game_state.update_game_tick()

            move_count += 1

            # 防止无限循环
            if move_count > 1000:
                print(f"Game {game_id}: Too many moves, forcing end")
                break

        # 确定胜负
        result = game_state.get_result() if hasattr(game_state, 'get_result') else 0
        winner = game_state.winner

        # 为每个数据点添加价值标签
        for i, data in enumerate(training_data):
            player = data['player']
            if winner:
                # 从该玩家视角的价值
                value = 1.0 if winner.id == player else -1.0
            else:
                value = 0.0  # 平局

            data['value'] = value

        print(f"Game {game_id}: Finished after {move_count} moves, winner: {winner.name if winner else 'Draw'}")

        return training_data


class SelfPlayManager:
    """自对弈管理器"""

    def __init__(self, model: GameCNN, replay_buffer_size: int = 10000,
                 num_parallel_games: int = 4, device=None):
        self.model = model
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.replay_buffer = deque(maxlen=replay_buffer_size)
        self.num_parallel_games = num_parallel_games

    def generate_games(self, num_games: int) -> List[Dict[str, Any]]:
        """生成多场自对弈游戏"""
        all_data = []

        for game_id in range(num_games):
            agent = SelfPlayAgent(self.model, self.device)
            game_data = agent.play_game(game_id)
            all_data.extend(game_data)

            # 添加到回放缓冲区
            for data in game_data:
                self.replay_buffer.append(data)

            if (game_id + 1) % 10 == 0:
                print(f"Generated {game_id + 1}/{num_games} games, buffer size: {len(self.replay_buffer)}")

        return all_data

    def get_training_batch(self, batch_size: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """从回放缓冲区获取训练批次"""
        if len(self.replay_buffer) < batch_size:
            batch_size = len(self.replay_buffer)

        # 随机采样
        batch_data = random.sample(self.replay_buffer, batch_size)

        # 转换为张量
        states = []
        policies = []
        values = []

        for data in batch_data:
            states.append(data['state'])
            policies.append(data['policy'])
            values.append(data['value'])

        states_tensor = torch.FloatTensor(np.array(states)).to(self.device)
        policies_tensor = torch.FloatTensor(np.array(policies)).to(self.device)
        values_tensor = torch.FloatTensor(np.array(values)).unsqueeze(1).to(self.device)

        return states_tensor, policies_tensor, values_tensor

    def save_replay_buffer(self, path: str):
        """保存回放缓冲区"""
        import pickle
        with open(path, 'wb') as f:
            pickle.dump(list(self.replay_buffer), f)

    def load_replay_buffer(self, path: str):
        """加载回放缓冲区"""
        import pickle
        with open(path, 'rb') as f:
            data = pickle.load(f)
        self.replay_buffer.extend(data)