"""
AlphaZero风格的神经网络
输出策略分布和价值估计
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple


class ResidualBlock(nn.Module):
    """残差块"""

    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += residual
        out = F.relu(out)
        return out


class GameCNN(nn.Module):
    """游戏专用的CNN网络"""

    def __init__(self, input_channels: int = 9, num_res_blocks: int = 10,
                 num_actions: int = 1600, hidden_dim: int = 256):
        super().__init__()

        # 输入卷积层
        self.conv_input = nn.Conv2d(input_channels, hidden_dim, kernel_size=3, padding=1, bias=False)
        self.bn_input = nn.BatchNorm2d(hidden_dim)

        # 残差塔
        self.res_blocks = nn.ModuleList([
            ResidualBlock(hidden_dim) for _ in range(num_res_blocks)
        ])

        # 策略头
        self.conv_policy = nn.Conv2d(hidden_dim, 32, kernel_size=1, bias=False)
        self.bn_policy = nn.BatchNorm2d(32)
        self.fc_policy = nn.Linear(32 * 20 * 20, num_actions)

        # 价值头
        self.conv_value = nn.Conv2d(hidden_dim, 4, kernel_size=1, bias=False)
        self.bn_value = nn.BatchNorm2d(4)
        self.fc_value1 = nn.Linear(4 * 20 * 20, 256)
        self.fc_value2 = nn.Linear(256, 1)

        # 初始化权重
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Conv2d, nn.Linear)):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: (batch_size, 9, 20, 20)

        Returns:
            policy_logits: (batch_size, 1600)
            value: (batch_size, 1)
        """
        batch_size = x.size(0)

        # 输入卷积
        x = F.relu(self.bn_input(self.conv_input(x)))

        # 残差块
        for res_block in self.res_blocks:
            x = res_block(x)

        # 策略头
        policy = F.relu(self.bn_policy(self.conv_policy(x)))
        policy = policy.view(batch_size, -1)
        policy_logits = self.fc_policy(policy)

        # 价值头
        value = F.relu(self.bn_value(self.conv_value(x)))
        value = value.view(batch_size, -1)
        value = F.relu(self.fc_value1(value))
        value = torch.tanh(self.fc_value2(value))

        return policy_logits, value

    def predict(self, state: np.ndarray, device: torch.device = None) -> Tuple[np.ndarray, float]:
        """
        预测给定状态的策略和价值

        Args:
            state: (9, 20, 20) numpy数组
            device: 计算设备

        Returns:
            policy: (1600,) 策略分布
            value: 价值估计
        """
        if device is None:
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.eval()
        with torch.no_grad():
            # 添加batch维度
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(device)
            policy_logits, value = self(state_tensor)

            # 转换为概率分布
            policy = F.softmax(policy_logits, dim=1)

            return policy.cpu().numpy()[0], value.item()

    def save_model(self, path: str):
        """保存模型"""
        torch.save({
            'model_state_dict': self.state_dict(),
            'config': {
                'input_channels': 9,
                'num_res_blocks': len(self.res_blocks),
                'num_actions': self.fc_policy.out_features,
                'hidden_dim': self.conv_input.out_channels
            }
        }, path)

    @classmethod
    def load_model(cls, path: str, device: torch.device = None):
        """加载模型"""
        if device is None:
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        checkpoint = torch.load(path, map_location=device)
        config = checkpoint['config']

        model = cls(
            input_channels=config['input_channels'],
            num_res_blocks=config['num_res_blocks'],
            num_actions=config['num_actions'],
            hidden_dim=config['hidden_dim']
        )
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(device)

        return model