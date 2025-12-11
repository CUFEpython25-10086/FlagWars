#!/usr/bin/env python3
"""
FlagWars游戏服务器启动脚本

该脚本是FlagWars多人夺旗游戏的服务器入口点，负责：
1. 配置Python路径，确保能找到src目录下的模块
2. 导入并启动游戏服务器主函数
3. 处理命令行参数和环境配置

使用方法:
    python run_server.py                    # 使用默认配置启动
    python run_server.py --port 8080        # 指定端口启动
    python run_server.py --debug            # 启用调试模式

作者: FlagWars开发团队
版本: 1.0.0
"""

import sys
import os
import argparse

def setup_python_path() -> None:
    """
    配置Python模块搜索路径
    
    该函数将项目的src目录添加到Python的模块搜索路径中，
    确保能够正确导入flagwars包及其子模块。
    
    这样做的好处：
    1. 允许直接从项目根目录运行脚本
    2. 保持模块导入的一致性
    3. 避免相对导入的复杂性
    """
    # 获取当前脚本所在目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(current_dir, 'src')
    
    # 将src目录插入到Python路径的最前面，优先级最高
    sys.path.insert(0, src_path)


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的命令行参数对象
    """
    parser = argparse.ArgumentParser(
        description='FlagWars多人夺旗游戏服务器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                    # 使用默认配置启动服务器
  %(prog)s --port 8080        # 在8080端口启动服务器
  %(prog)s --debug --port 9000  # 启用调试模式并指定端口
        """
    )
    
    parser.add_argument(
        '--port', 
        type=int, 
        default=8888,
        help='服务器监听端口 (默认: 8888)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式 (默认: False)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='服务器绑定地址 (默认: 0.0.0.0)'
    )
    
    return parser.parse_args()


def validate_environment() -> bool:
    """
    验证运行环境是否满足要求
    
    Returns:
        bool: 环境验证是否通过
    """
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("错误: 需要Python 3.8或更高版本")
        return False
    
    # 检查必要的目录是否存在
    required_dirs = ['src', 'music', 'icons']
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            print(f"警告: 目录 '{dir_name}' 不存在，某些功能可能无法正常工作")
    
    return True


def main() -> None:
    """
    主函数 - 服务器启动入口点
    
    这是整个服务器程序的入口点，负责：
    1. 配置Python环境
    2. 解析命令行参数
    3. 验证运行环境
    4. 导入并启动服务器主逻辑
    """
    try:
        # 1. 配置Python模块路径
        setup_python_path()
        
        # 2. 解析命令行参数
        args = parse_arguments()
        
        # 3. 验证运行环境
        if not validate_environment():
            sys.exit(1)
        
        # 4. 导入服务器主模块
        from flagwars.server import main as server_main
        
        # 5. 启动服务器
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"""
{'='*70}
🏆  FlagWars 多人在线夺旗游戏服务器
{'='*70}

🎮  游戏信息
   📋 游戏类型: 多人在线夺旗对战
   📦 版本信息: v1.0.0

🌐 网络配置
   📍 监听地址: {args.host}
   🔌 监听端口: {args.port}
   🔧 调试模式: {'🟢 开启' if args.debug else '🔴 关闭'}

⏰ 启动时间: {current_time}

🚀 服务器正在启动中，请稍候...
{'='*70}
        """)
        
        # 启动服务器，传递命令行参数
        server_main(
            port=args.port,
            debug=args.debug,
            host=args.host
        )
        
    except KeyboardInterrupt:
        print("\n\n🛑 收到中断信号，正在关闭服务器...")
    except ImportError as e:
        print(f"❌ 模块导入错误: {e}")
        print("请确保所有依赖都已正确安装")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        if args.debug if 'args' in locals() else False:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        print("👋 FlagWars服务器已关闭")


if __name__ == "__main__":
    """
    程序入口点 - 当脚本被直接执行时调用main函数
    
    这是Python脚本的标准入口模式：
    - 当脚本被直接执行时，__name__ == "__main__" 为真
    - 当脚本被其他模块导入时，__name__ 为模块名，不会执行main
    """
    main()