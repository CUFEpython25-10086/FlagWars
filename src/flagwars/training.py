"""
训练循环
"""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Tuple, List, Dict, Any
import time
from pathlib import Path

from neural_network import GameCNN
from self_play import SelfPlayManager
from config import TrainingConfig


class Trainer:
    """训练器"""

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.device = torch.device(config.device)

        # 创建模型
        self.model = GameCNN(
            input_channels=9,
            num_res_blocks=config.num_res_blocks,
            num_actions=1600,
            hidden_dim=config.hidden_dim
        ).to(self.device)

        # 创建优化器
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay
        )

        # 学习率调度器
        self.scheduler = optim.lr_scheduler.MultiStepLR(
            self.optimizer,
            milestones=config.lr_milestones,
            gamma=config.lr_gamma
        )

        # 自对弈管理器
        self.self_play_manager = SelfPlayManager(
            self.model,
            replay_buffer_size=config.replay_buffer_size,
            device=self.device
        )

        # 损失函数
        self.policy_loss_fn = nn.CrossEntropyLoss()
        self.value_loss_fn = nn.MSELoss()

        # 训练历史
        self.history = {
            'policy_loss': [],
            'value_loss': [],
            'total_loss': [],
            'value_accuracy': []
        }

    def train_step(self, states: torch.Tensor, target_policies: torch.Tensor,
                   target_values: torch.Tensor) -> Tuple[float, float, float]:
        """单次训练步骤"""
        self.model.train()

        # 前向传播
        policy_logits, values = self.model(states)

        # 计算损失
        policy_loss = self.policy_loss_fn(policy_logits, target_policies.argmax(dim=1))
        value_loss = self.value_loss_fn(values, target_values)
        total_loss = policy_loss + self.config.value_loss_weight * value_loss

        # 反向传播
        self.optimizer.zero_grad()
        total_loss.backward()

        # 梯度裁剪
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)

        self.optimizer.step()

        # 计算价值准确率
        value_predictions = torch.sign(values)
        value_targets = torch.sign(target_values)
        value_accuracy = (value_predictions == value_targets).float().mean().item()

        return policy_loss.item(), value_loss.item(), total_loss.item(), value_accuracy

    def train_epoch(self, epoch: int) -> Dict[str, Any]:
        """训练一个周期"""
        epoch_start_time = time.time()

        # 生成自对弈数据
        print(f"Epoch {epoch}: Generating self-play games...")
        self.self_play_manager.generate_games(self.config.games_per_epoch)

        # 训练步骤
        epoch_policy_loss = []
        epoch_value_loss = []
        epoch_total_loss = []
        epoch_value_accuracy = []

        num_batches = max(1, len(self.self_play_manager.replay_buffer) // self.config.batch_size)

        print(f"Epoch {epoch}: Training on {num_batches} batches...")

        for batch_idx in range(num_batches):
            # 获取训练批次
            states, policies, values = self.self_play_manager.get_training_batch(
                self.config.batch_size
            )

            # 训练步骤
            policy_loss, value_loss, total_loss, value_accuracy = self.train_step(
                states, policies, values
            )

            # 记录损失
            epoch_policy_loss.append(policy_loss)
            epoch_value_loss.append(value_loss)
            epoch_total_loss.append(total_loss)
            epoch_value_accuracy.append(value_accuracy)

            if (batch_idx + 1) % 10 == 0:
                print(f"  Batch {batch_idx + 1}/{num_batches}: "
                      f"Policy Loss: {policy_loss:.4f}, "
                      f"Value Loss: {value_loss:.4f}, "
                      f"Value Acc: {value_accuracy:.2%}")

        # 更新学习率
        self.scheduler.step()

        # 计算平均损失
        avg_policy_loss = np.mean(epoch_policy_loss)
        avg_value_loss = np.mean(epoch_value_loss)
        avg_total_loss = np.mean(epoch_total_loss)
        avg_value_accuracy = np.mean(epoch_value_accuracy)

        # 保存到历史
        self.history['policy_loss'].append(avg_policy_loss)
        self.history['value_loss'].append(avg_value_loss)
        self.history['total_loss'].append(avg_total_loss)
        self.history['value_accuracy'].append(avg_value_accuracy)

        epoch_time = time.time() - epoch_start_time

        print(f"Epoch {epoch} finished in {epoch_time:.1f}s: "
              f"Total Loss: {avg_total_loss:.4f}, "
              f"Policy Loss: {avg_policy_loss:.4f}, "
              f"Value Loss: {avg_value_loss:.4f}, "
              f"Value Acc: {avg_value_accuracy:.2%}")

        return {
            'policy_loss': avg_policy_loss,
            'value_loss': avg_value_loss,
            'total_loss': avg_total_loss,
            'value_accuracy': avg_value_accuracy,
            'epoch_time': epoch_time
        }

    def train(self, num_epochs: int = None, save_dir: str = "checkpoints"):
        """完整训练循环"""
        if num_epochs is None:
            num_epochs = self.config.num_epochs

        # 创建保存目录
        save_path = Path(save_dir)
        save_path.mkdir(exist_ok=True)

        print(f"Starting training for {num_epochs} epochs...")
        print(f"Device: {self.device}")
        print(f"Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")

        for epoch in range(1, num_epochs + 1):
            # 训练一个周期
            metrics = self.train_epoch(epoch)

            # 保存检查点
            if epoch % self.config.save_interval == 0:
                checkpoint_path = save_path / f"model_epoch_{epoch}.pt"
                self.model.save_model(str(checkpoint_path))
                print(f"Saved checkpoint to {checkpoint_path}")

            # 评估模型
            if epoch % self.config.eval_interval == 0:
                self.evaluate(epoch)

            # 保存训练历史
            if epoch % 10 == 0:
                history_path = save_path / "training_history.pkl"
                import pickle
                with open(history_path, 'wb') as f:
                    pickle.dump(self.history, f)

    def evaluate(self, epoch: int, num_games: int = 20):
        """评估模型"""
        print(f"Evaluating model at epoch {epoch}...")

        # 这里可以添加评估逻辑，例如与旧版本模型对战
        # 由于时间关系，这里仅打印评估开始消息
        pass

    def plot_training_history(self, save_path: str = None):
        """绘制训练历史"""
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(12, 8))

        epochs = range(1, len(self.history['total_loss']) + 1)

        # 总损失
        axes[0, 0].plot(epochs, self.history['total_loss'])
        axes[0, 0].set_title('Total Loss')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].grid(True)

        # 策略损失
        axes[0, 1].plot(epochs, self.history['policy_loss'])
        axes[0, 1].set_title('Policy Loss')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Loss')
        axes[0, 1].grid(True)

        # 价值损失
        axes[1, 0].plot(epochs, self.history['value_loss'])
        axes[1, 0].set_title('Value Loss')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Loss')
        axes[1, 0].grid(True)

        # 价值准确率
        axes[1, 1].plot(epochs, self.history['value_accuracy'])
        axes[1, 1].set_title('Value Accuracy')
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('Accuracy')
        axes[1, 1].grid(True)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
        else:
            plt.show()