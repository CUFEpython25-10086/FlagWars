"""
主训练脚本
"""
import argparse
from training import Trainer
from src import flagwars
from config import *


def main():
    parser = argparse.ArgumentParser(description='Train CNN+MCTS model for the game')
    parser.add_argument('--epochs', type=int, default=100, help='Number of training epochs')
    parser.add_argument('--games-per-epoch', type=int, default=100, help='Games per epoch')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--device', type=str, default='cuda', help='Device to use')
    parser.add_argument('--save-dir', type=str, default='checkpoints', help='Directory to save checkpoints')
    parser.add_argument('--resume', type=str, help='Path to checkpoint to resume from')

    args = parser.parse_args()

    # 创建配置
    config = TrainingConfig(
        device=args.device,
        num_epochs=args.epochs,
        games_per_epoch=args.games_per_epoch,
        batch_size=args.batch_size,
        learning_rate=args.lr
    )

    # 创建训练器
    trainer = Trainer(config)

    # 恢复训练（如果指定）
    if args.resume:
        print(f"Resuming from checkpoint: {args.resume}")
        # 这里需要实现恢复逻辑

    # 开始训练
    trainer.train(num_epochs=args.epochs, save_dir=args.save_dir)

    # 绘制训练历史
    trainer.plot_training_history(save_path=f"{args.save_dir}/training_history.png")


if __name__ == '__main__':
    main()