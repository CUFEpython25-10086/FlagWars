"""
训练配置
"""
from dataclasses import dataclass
from typing import List

@dataclass
class TrainingConfig:
    """训练配置"""

    # 设备配置
    device: str = "cuda"  # "cuda" 或 "cpu"

    # 模型架构
    num_res_blocks: int = 10
    hidden_dim: int = 256

    # 训练参数
    num_epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    weight_decay: float = 1e-4
    value_loss_weight: float = 1.0
    max_grad_norm: float = 1.0

    # 自对弈参数
    games_per_epoch: int = 100
    replay_buffer_size: int = 10000
    num_simulations: int = 800
    temperature_threshold: int = 10

    # 学习率调度
    lr_milestones: List[int] = None
    lr_gamma: float = 0.1

    # 保存和评估
    save_interval: int = 5
    eval_interval: int = 10

    def __post_init__(self):
        if self.lr_milestones is None:
            self.lr_milestones = [30, 60, 90]

@dataclass
class MCTSConfig:
    """MCTS配置"""

    num_simulations: int = 800
    c_puct: float = 1.0
    temperature: float = 1.0
    dirichlet_alpha: float = 0.3  # 狄利克雷噪声参数
    dirichlet_epsilon: float = 0.25  # 噪声混合比例