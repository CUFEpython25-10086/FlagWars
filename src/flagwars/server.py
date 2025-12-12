"""
FlagWars游戏服务器 - 基于Tornado

这是FlagWars多人夺旗游戏的核心服务器模块，负责：
1. WebSocket通信处理 - 与客户端进行实时通信
2. 游戏状态管理 - 管理游戏房间、玩家状态和游戏逻辑
3. 房间系统 - 创建、加入、管理游戏房间
4. 实时游戏更新 - 处理游戏中的各种操作和状态同步

主要组件：
- GameWebSocketHandler: 处理WebSocket连接和客户端消息
- GameManager: 管理游戏逻辑、房间和玩家状态
- 各种消息处理方法: 处理客户端发送的不同类型消息

作者: FlagWars开发团队
版本: 1.0.0
"""

import json
import logging
import asyncio
import time
from typing import Dict, Set, Any
from tornado import web, websocket, ioloop, httpserver

from .models import GameState, Player, TerrainType
from .database import db
from .auth import auth_routes


class GameWebSocketHandler(websocket.WebSocketHandler):
    """
    WebSocket连接处理器 - 负责与客户端的实时通信
    
    该类是Tornado WebSocket处理器的子类，专门用于处理FlagWars游戏的
    实时通信需求。每个WebSocket连接对应一个客户端连接。
    
    主要功能：
    1. 处理客户端连接和断开
    2. 解析和路由客户端消息
    3. 管理玩家会话状态
    4. 与GameManager协作处理游戏逻辑
    5. 发送游戏状态更新给客户端
    
    消息类型：
    - create_room: 创建新游戏房间
    - join_room: 加入指定房间
    - join_game: 加入游戏（自动创建或加入房间）
    - get_rooms: 获取可用房间列表
    - player_ready: 设置玩家准备状态
    - move_soldiers: 移动士兵
    - get_game_state: 获取当前游戏状态
    - play_again: 重新开始游戏
    
    属性:
        game_manager: GameManager实例，用于处理游戏逻辑
        player_id: 当前玩家的唯一标识符
        game_id: 当前游戏房间的标识符
        user_id: 登录用户的数据库ID（如果已登录）
    """
    
    def initialize(self, game_manager: 'GameManager') -> None:
        """
        初始化WebSocket处理器
        
        Args:
            game_manager: 游戏管理器实例，用于处理游戏逻辑
        """
        self.game_manager = game_manager
        self.player_id = None  # 玩家在当前游戏中的ID
        self.game_id = None    # 当前游戏房间ID
        self.user_id = None    # 登录用户的数据库ID
    
    def open(self) -> None:
        """
        WebSocket连接建立时的回调方法
        
        当客户端与服务器建立WebSocket连接时调用此方法。
        主要职责：
        1. 验证用户会话（如果有登录状态）
        2. 记录连接日志
        3. 初始化用户状态
        
        注意：
        - 匿名用户也可以建立连接
        - 已登录用户的会话会被验证
        """
        logging.info("🔗 WebSocket连接建立")
        
        # 检查客户端是否提供了会话令牌（登录状态验证）
        session_token = self.get_cookie("session_token")
        if session_token:
            user = db.verify_session(session_token)
            if user:
                self.user_id = user['id']
                logging.info(f"👤 用户 {user['username']} (ID: {user['id']}) 已连接")
            else:
                logging.warning("⚠️ 无效的会话令牌")
        else:
            logging.info("👤 匿名用户连接")
    
    def on_message(self, message: str) -> None:
        """
        处理客户端发送的WebSocket消息
        
        这是WebSocket通信的核心方法，负责接收和路由客户端消息。
        支持的消息类型包括房间管理、游戏操作和状态查询等。
        
        消息路由：
        - join_game: 加入游戏（自动创建或加入房间）
        - create_room: 创建新游戏房间
        - join_room: 加入指定房间
        - get_rooms: 获取可用房间列表
        - player_ready: 设置玩家准备状态
        - move_soldiers: 移动士兵
        - get_game_state: 获取当前游戏状态
        - play_again: 重新开始游戏
        
        Args:
            message: 客户端发送的JSON格式消息字符串
            
        消息格式:
            {
                "type": "消息类型",
                "data": {消息数据}
            }
            
        错误处理:
            - JSON格式错误：记录错误日志，返回错误消息
            - 未知消息类型：记录警告日志，返回错误消息
            - 其他异常：记录错误日志，返回通用错误消息
            
        注意：
        - 该方法是异步的，但不需要显式标记为async
        - 错误发生时需要向客户端发送错误反馈
        """
        try:
            # 解析客户端发送的JSON消息
            data = json.loads(message)
            message_type = data.get('type')
            
            # 根据消息类型路由到对应的处理方法
            if message_type == 'join_game':
                self._handle_join_game(data)
            elif message_type == 'create_room':
                self._handle_create_room(data)
            elif message_type == 'join_room':
                self._handle_join_room(data)
            elif message_type == 'get_rooms':
                self._handle_get_rooms()
            elif message_type == 'player_ready':
                self._handle_player_ready()
            elif message_type == 'spectator_mode':
                self._handle_spectator_mode()
            elif message_type == 'cancel_spectator_mode':
                self._handle_cancel_spectator_mode()
            elif message_type == 'move_soldiers':
                self._handle_move_soldiers(data)
            elif message_type == 'get_game_state':
                self._handle_get_game_state()
            elif message_type == 'play_again':
                self._handle_play_again()
            else:
                logging.warning(f"⚠️ 未知消息类型: {message_type}")
                self.send_error(f"未知消息类型: {message_type}")
            
        except json.JSONDecodeError:
            logging.error(f"❌ JSON解析错误: {message}")
            self.send_error("消息格式错误，请发送有效的JSON")
        except Exception as e:
            logging.error(f"💥 处理消息时发生错误: {str(e)}", exc_info=True)
            self.send_error("处理消息时发生内部错误")
    
    def _handle_create_room(self, data: Dict[str, Any]) -> None:
        """
        处理创建房间请求
        
        该方法处理客户端创建新游戏房间的请求。创建房间后，
        创建者会自动加入该房间并成为房主。
        
        流程：
        1. 获取玩家名称（优先使用已登录用户名）
        2. 通过GameManager创建新房间
        3. 房主自动加入房间
        4. 建立WebSocket连接映射
        5. 向客户端发送房间创建成功的响应
        
        Args:
            data: 客户端发送的消息数据，包含玩家名称等信息
                - player_name: 玩家显示名称（可选）
        
        响应消息:
            - type: 'room_created'
            - room_id: 房间唯一标识符
            - game_id: 游戏实例ID
            - player_id: 当前玩家在游戏中的ID
            - game_state: 当前游戏状态
            
        错误响应:
            - type: 'create_room_failed'
            - message: 错误描述信息
        """
        player_name = data.get('player_name', '玩家')
        
        # 如果用户已登录，优先使用数据库中的用户名
        if self.user_id:
            user = db.verify_session(self.get_cookie("session_token"))
            if user:
                player_name = user['username']
        
        # 通过GameManager创建新房间
        room_id = self.game_manager.create_room()
        
        # 房主自动加入刚创建的房间
        game_id, player_id, error = self.game_manager.join_room(room_id, player_name, self.user_id)
        
        if error:
            # 房间创建或加入失败，返回错误信息
            response = {
                'type': 'create_room_failed',
                'message': error
            }
            self.write_message(json.dumps(response))
            self.close()
            return
        
        # 保存玩家和游戏信息到WebSocket处理器
        self.player_id = player_id
        self.game_id = game_id
        
        # 将WebSocket连接添加到GameManager的玩家连接映射中
        # 这样就可以向特定玩家发送消息
        self.game_manager.add_player_connection(game_id, player_id, self)
        
        # 发送房间创建成功响应
        response = {
            'type': 'room_created',
            'room_id': room_id,
            'game_id': game_id,
            'player_id': player_id,
            'game_state': self.game_manager.get_game_state(game_id, player_id)
        }
        self.write_message(json.dumps(response, default=str))
    
    def _handle_join_room(self, data):
        """处理加入房间请求"""
        room_id = data.get('room_id')
        player_name = data.get('player_name', '玩家')
        
        if not room_id:
            self.send_error("房间ID不能为空")
            self.close()
            return
        
        # 如果用户已登录，使用用户名
        if self.user_id:
            user = db.verify_session(self.get_cookie("session_token"))
            if user:
                player_name = user['username']
        
        # 加入房间
        game_id, player_id, error = self.game_manager.join_room(room_id, player_name, self.user_id)
        
        if error:
            response = {
                'type': 'join_room_failed',
                'message': error
            }
            self.write_message(json.dumps(response))
            self.close()
            return
        
        self.player_id = player_id
        self.game_id = game_id
        
        # 将WebSocket处理器添加到玩家字典
        self.game_manager.add_player_connection(game_id, player_id, self)
        
        # 发送房间加入成功信息
        response = {
            'type': 'room_joined',
            'room_id': room_id,
            'game_id': game_id,
            'player_id': player_id,
            'game_state': self.game_manager.get_game_state(game_id, player_id)
        }
        self.write_message(json.dumps(response, default=str))
    
    def _handle_get_rooms(self):
        """处理获取房间列表请求"""
        rooms = self.game_manager.get_available_rooms()
        
        response = {
            'type': 'rooms_list',
            'rooms': rooms
        }
        self.write_message(json.dumps(response))
    
    def _handle_join_game(self, data):
        """处理加入游戏请求"""
        player_name = data.get('player_name', '玩家')
        
        # 创建或加入游戏
        game_id, player_id = self.game_manager.create_or_join_game(player_name)
        
        # 如果返回None，表示游戏已开始，拒绝加入
        if game_id is None and player_id is None:
            response = {
                'type': 'join_rejected',
                'message': '游戏已开始，无法加入'
            }
            self.write_message(json.dumps(response))
            return
        
        self.player_id = player_id
        self.game_id = game_id
        
        # 将WebSocket处理器添加到玩家字典
        self.game_manager.add_player_connection(game_id, player_id, self)
        
        # 发送游戏信息
        response = {
            'type': 'game_joined',
            'game_id': game_id,
            'room_id': game_id,  # 添加房间ID，在这个实现中game_id就是room_id
            'player_id': player_id,
            'game_state': self.game_manager.get_game_state(game_id)
        }
        self.write_message(json.dumps(response, default=str))
    
    def _handle_player_ready(self):
        """处理玩家准备请求"""
        if not self.player_id or not self.game_id:
            self.send_error("请先加入游戏")
            return
        
        # 设置玩家准备状态
        game_started = self.game_manager.set_player_ready(self.game_id, self.player_id)
        
        # 发送准备状态更新
        response = {
            'type': 'player_ready_updated',
            'game_state': self.game_manager.get_game_state(self.game_id),
            'game_started': game_started
        }
        self.write_message(json.dumps(response, default=str))
        
        # 如果游戏开始，广播给所有玩家
        if game_started:
            self.game_manager.broadcast_game_start(self.game_id)
    
    def _handle_spectator_mode(self):
        """处理玩家选择观战模式请求"""
        if not self.player_id or not self.game_id:
            self.send_error("请先加入游戏")
            return
        
        # 设置玩家为观战模式
        success = self.game_manager.set_voluntary_spectator(self.game_id, self.player_id)
        
        if success:
            # 发送观战模式设置成功消息
            response = {
                'type': 'spectator_mode_set',
                'message': '已成功设置为观战模式',
                'game_state': self.game_manager.get_game_state(self.game_id)
            }
            self.write_message(json.dumps(response, default=str))
            
            # 广播玩家状态更新给房间内所有玩家
            self.game_manager.broadcast_player_status_update(self.game_id)
        else:
            self.send_error("设置观战模式失败")
    
    def _handle_cancel_spectator_mode(self):
        """处理玩家取消观战模式请求"""
        if not self.player_id or not self.game_id:
            self.send_error("请先加入游戏")
            return
        
        # 取消玩家观战模式
        success = self.game_manager.cancel_voluntary_spectator(self.game_id, self.player_id)
        
        if success:
            # 发送观战模式取消成功消息
            response = {
                'type': 'cancel_spectator_mode_set',
                'message': '已成功取消观战模式',
                'game_state': self.game_manager.get_game_state(self.game_id)
            }
            self.write_message(json.dumps(response, default=str))
            
            # 广播玩家状态更新给房间内所有玩家
            self.game_manager.broadcast_player_status_update(self.game_id)
        else:
            self.send_error("取消观战模式失败")
    
    def _handle_move_soldiers(self, data):
        """处理移动士兵请求"""
        if not self.player_id or not self.game_id:
            self.send_error("请先加入游戏")
            return
        
        from_x = data.get('from_x')
        from_y = data.get('from_y')
        to_x = data.get('to_x')
        to_y = data.get('to_y')
        
        success = self.game_manager.move_soldiers(
            self.game_id, self.player_id, from_x, from_y, to_x, to_y
        )
        
        response = {
            'type': 'move_result',
            'success': success,
            'game_state': self.game_manager.get_game_state(self.game_id, self.player_id)
        }
        self.write_message(json.dumps(response, default=str))
    
    def _handle_get_game_state(self):
        """处理获取游戏状态请求"""
        if not self.game_id:
            self.send_error("请先加入游戏")
            return
        
        response = {
            'type': 'game_state',
            'game_state': self.game_manager.get_game_state(self.game_id, self.player_id)
        }
        self.write_message(json.dumps(response, default=str))
    
    def _handle_play_again(self):
        """处理再来一局请求"""
        if not self.game_id:
            self.send_error("请先加入游戏")
            return
        
        # 重置游戏状态
        success = self.game_manager.reset_game(self.game_id)
        
        if success:
            # 广播游戏重置消息给所有玩家
            self.game_manager.broadcast_game_reset(self.game_id)
            
            response = {
                'type': 'play_again_success',
                'message': '游戏已重置，请准备开始新一局'
            }
            self.write_message(json.dumps(response))
        else:
            self.send_error("重置游戏失败")
    
    def send_error(self, error_message):
        """发送错误消息"""
        response = {
            'type': 'error',
            'message': error_message
        }
        self.write_message(json.dumps(response))
    
    def on_close(self):
        """WebSocket连接关闭"""
        logging.info("WebSocket连接关闭")
        if self.game_id and self.player_id:
            self.game_manager.leave_game(self.game_id, self.player_id)


class GameManager:
    """
    游戏状态管理器 - 负责整个FlagWars游戏的核心逻辑
    
    该类是游戏服务器的核心组件，负责管理：
    1. 多房间系统 - 维护多个独立的游戏房间
    2. 玩家管理 - 跟踪玩家状态、连接和准备状态
    3. 游戏状态 - 管理游戏进程、计时和规则执行
    4. 实时更新 - 定期更新游戏状态并广播给所有玩家
    5. WebSocket连接管理 - 维护玩家与服务器的连接映射
    
    主要特性：
    - 支持最多8个玩家同时游戏
    - 每个玩家有独特的颜色标识
    - 自动生成合理的出生点位置
    - 游戏状态实时同步
    - 支持游戏重置和重新开始
    
    属性说明：
        games: 游戏房间映射 {room_id: GameState}
        players: 玩家连接映射 {room_id: {player_id: handler}}
        connections: WebSocket连接映射 {room_id: {player_id: handler}}
        player_ready_states: 玩家准备状态 {room_id: {player_id: ready}}
        player_user_mapping: 玩家ID与用户ID的映射
        game_start_times: 游戏开始时间记录
        last_broadcast_time: 最后广播时间（用于频率控制）
        game_over_games: 已结束游戏集合
        game_countdowns: 游戏倒计时状态
        countdown_tasks: 倒计时任务
        room_colors: 房间颜色使用记录
    """
    
    def __init__(self) -> None:
        """初始化游戏管理器"""
        # 核心数据存储
        self.games: Dict[str, GameState] = {}  # 所有游戏房间
        self.players: Dict[str, Dict[int, GameWebSocketHandler]] = {}  # 玩家连接
        self.connections: Dict[str, Dict[int, GameWebSocketHandler]] = {}  # WebSocket连接
        self.player_ready_states: Dict[str, Dict[int, bool]] = {}  # 玩家准备状态
        self.player_user_mapping: Dict[int, int] = {}  # 玩家ID与用户ID映射
        self.game_start_times: Dict[str, float] = {}  # 游戏开始时间
        self.last_broadcast_time: Dict[str, float] = {}  # 最后广播时间
        self.game_over_games: Set[str] = set()  # 已结束游戏
        
        # 玩家和房间ID生成器
        self.next_player_id = 1  # 玩家ID自增器
        self.next_room_id = 1000  # 房间ID从1000开始
        self.available_room_ids = set()  # 已释放的房间号集合
        
        # 游戏控制相关
        self.game_countdowns: Dict[str, int] = {}  # 房间倒计时状态
        self.countdown_tasks: Dict[str, asyncio.Task] = {}  # 倒计时任务
        
        # 玩家颜色系统
        self.player_colors = [
            "#FF0000",  # 红色
            "#0000FF",  # 蓝色
            "#00FF00",  # 绿色
            "#FFFF00",  # 黄色
            "#FF00FF",  # 紫色
            "#00FFFF",  # 青色
            "#FFA500",  # 橙色
            "#800080"   # 深紫色
        ]
        
        self.color_names = ["Red", "Green", "Blue", "Gold", "Magenta", "Cyan", "Orange", "Purple"]
        self.room_colors: Dict[str, Set[str]] = {}  # 房间颜色使用记录
        
        # 启动游戏主循环
        self._start_game_loop()
    
    def _start_game_loop(self) -> None:
        """
        启动游戏主循环
        
        创建一个异步任务，定期更新所有游戏的状态。
        这个循环负责：
        1. 更新游戏逻辑（如倒计时、游戏进程）
        2. 检查游戏结束条件
        3. 清理过期的游戏房间
        4. 广播游戏状态更新给所有玩家
        
        更新频率：每0.6秒一次，既保证游戏流畅性又避免过度网络通信
        """
        async def game_loop():
            """异步游戏主循环"""
            while True:
                await asyncio.sleep(0.6)  # 每0.6秒更新一次
                self._update_all_games()
        
        # 将循环任务添加到Tornado的IOLoop中
        ioloop.IOLoop.current().add_callback(game_loop)
    
    def create_room(self) -> str:
        """
        创建新的游戏房间
        
        房间创建时会：
        1. 分配房间ID（优先使用已释放的最小ID）
        2. 创建新的GameState实例
        3. 初始化玩家列表和准备状态
        
        Returns:
            str: 新创建的房间ID
            
        Note:
            - 房间ID从1000开始递增
            - 已关闭的房间ID会被回收使用
        """
        # 如果有已释放的房间号，使用最小的可用房间号
        if self.available_room_ids:
            room_id_int = min(self.available_room_ids)
            self.available_room_ids.remove(room_id_int)
            room_id = str(room_id_int)
        else:
            # 否则使用next_room_id
            room_id = str(self.next_room_id)
            self.next_room_id += 1
        
        # 创建新游戏实例
        game_state = GameState()
        self.games[room_id] = game_state
        self.players[room_id] = {}
        self.player_ready_states[room_id] = {}
        
        return room_id
    
    def get_available_rooms(self) -> Dict[str, Dict]:
        """获取所有可用房间信息"""
        rooms = {}
        for room_id, game_state in self.games.items():
            # 只返回未开始的游戏房间
            if not game_state.game_started:
                rooms[room_id] = {
                    'room_id': room_id,
                    'player_count': len(game_state.players),
                    'max_players': 8,  # 最大8个玩家
                    'status': 'waiting' if not game_state.game_started else 'in_progress'
                }
        return rooms
    
    def join_room(self, room_id: str, player_name: str, user_id: int = None) -> tuple:
        """加入指定房间"""
        # 检查房间是否存在
        if room_id not in self.games:
            return None, None, "房间不存在"
        
        # 检查房间是否已开始
        if self.games[room_id].game_started:
            return None, None, "游戏已开始，无法加入"
        
        # 检查房间是否已满
        if len(self.games[room_id].players) >= 8:
            return None, None, "房间已满"
        
        # 创建玩家
        player_id = self.next_player_id
        self.next_player_id += 1
        
        # 初始化房间颜色跟踪（如果不存在）
        if room_id not in self.room_colors:
            self.room_colors[room_id] = set()
        
        # 获取当前房间内所有已使用的颜色
        used_colors = self.room_colors[room_id].copy()
        
        # 找出第一个未使用的颜色
        player_color = None
        
        for i, color in enumerate(self.player_colors):
            if color not in used_colors:
                player_color = color
                break
        
        # 如果所有颜色都已使用（理论上不会发生，因为最多8个玩家8种颜色）
        if player_color is None:
            # 使用轮询方式分配颜色
            player_index = len(self.players[room_id])
            player_color = self.player_colors[player_index % len(self.player_colors)]

        # 记录这个房间使用了这个颜色
        self.room_colors[room_id].add(player_color)
        
        player = Player(player_id, player_name, player_color)
        
        # 存储用户ID与游戏玩家ID的映射
        if user_id:
            self.player_user_mapping[player_id] = user_id
        
        # 获取游戏状态
        game_state = self.games[room_id]
        
        # 如果是第一个玩家，暂不生成出生点，等待所有玩家加入
        if len(self.players[room_id]) == 0:
            # 初始化出生点列表为空
            game_state.spawn_points = []
        
        # 分配基地位置
        player_index = len(self.players[room_id])
        
        # 如果还没有生成出生点，或者当前玩家数量超过了已生成的出生点数量
        if not hasattr(game_state, 'spawn_points') or player_index >= len(game_state.spawn_points):
            # 根据当前玩家数量+1生成新的出生点（设置最小距离为10）
            new_player_count = len(self.players[room_id]) + 1
            game_state.spawn_points = game_state.generate_random_spawn_points(new_player_count, min_distance=10)
        
        # 分配出生点（观战者不分配基地）
        if not player.voluntary_spectator:  # 只有非观战者才分配基地
            base_x, base_y = game_state.spawn_points[player_index]
            game_state.add_player(player, base_x, base_y)
        else:
            # 观战者加入游戏但不分配基地
            game_state.add_player_as_spectator(player)
        
        self.player_ready_states[room_id][player_id] = False  # 初始未准备
        
        return room_id, player_id, None  # 第三个参数为错误信息，None表示成功
    
    def create_or_join_game(self, player_name: str, room_id: str = None, user_id: int = None) -> tuple:
        """创建或加入游戏（保持向后兼容）"""
        if room_id:
            # 尝试加入指定房间
            return self.join_room(room_id, player_name, user_id)
        else:
            # 创建新房间并加入
            new_room_id = self.create_room()
            return self.join_room(new_room_id, player_name, user_id)

    def add_player_connection(self, game_id: str, player_id: int, handler):
        """添加玩家连接"""
        if game_id not in self.players:
            self.players[game_id] = {}
        if game_id not in self.connections:
            self.connections[game_id] = {}
            
        self.players[game_id][player_id] = handler
        self.connections[game_id][player_id] = handler
    
    def remove_player_connection(self, game_id: str, player_id: int):
        """移除玩家连接"""
        if game_id in self.players and player_id in self.players[game_id]:
            # 获取玩家信息以便清理颜色记录
            player = self.games[game_id].players.get(player_id)
            
            # 从房间颜色使用记录中移除该玩家的颜色
            if player and game_id in self.room_colors:
                self.room_colors[game_id].discard(player.color)
            
            del self.players[game_id][player_id]
        if game_id in self.connections and player_id in self.connections[game_id]:
            del self.connections[game_id][player_id]

    def set_player_ready(self, game_id: str, player_id: int) -> bool:
        """设置玩家准备状态，返回游戏是否开始"""
        if game_id not in self.player_ready_states or player_id not in self.player_ready_states[game_id]:
            return False
        
        # 切换准备状态
        self.player_ready_states[game_id][player_id] = not self.player_ready_states[game_id][player_id]
        
        # 获取游戏状态和玩家信息
        if game_id not in self.games:
            return False
        
        game_state = self.games[game_id]
        
        # 统计非观战者玩家的准备状态
        non_spectator_players = {}  # {player_id: ready_state}
        non_spectator_ready_count = 0
        
        for pid, ready_state in self.player_ready_states[game_id].items():
            player = game_state.players.get(pid)
            if player and not player.voluntary_spectator:
                non_spectator_players[pid] = ready_state
                if ready_state:
                    non_spectator_ready_count += 1
        
        total_non_spectator_players = len(non_spectator_players)
        all_non_spectator_ready = all(non_spectator_players.values())
        
        # 调试信息：打印准备状态（区分观战者和非观战者）
        total_players = len(self.player_ready_states[game_id])
        spectator_count = total_players - total_non_spectator_players
        logging.info(f"游戏 {game_id} 准备状态: 总玩家数={total_players} (非观战者={total_non_spectator_players}, 观战者={spectator_count}), 非观战者准备数={non_spectator_ready_count}, 非观战者全部准备={all_non_spectator_ready}")
        
        # 如果玩家取消准备，则取消倒计时（只检查非观战者）
        if not self.player_ready_states[game_id][player_id]:
            # 检查取消准备的玩家是否是非观战者
            player = game_state.players.get(player_id)
            if player and not player.voluntary_spectator:
                if game_id in self.countdown_tasks and not self.countdown_tasks[game_id].done():
                    self.countdown_tasks[game_id].cancel()
                    self.countdown_tasks.pop(game_id, None)
                    self.game_countdowns.pop(game_id, None)
                    logging.info(f"非观战者玩家 {player_id} 取消准备，倒计时已取消")
        
        # 如果至少有2个非观战者玩家、所有非观战者玩家都准备且游戏未开始，则开始倒计时
        if total_non_spectator_players >= 2 and all_non_spectator_ready and not game_state.game_started:
            # 开始3秒倒计时
            self.start_game_countdown(game_id)
            logging.info(f"游戏 {game_id} 开始3秒倒计时：{total_non_spectator_players}个非观战者玩家全部准备")
            return False  # 注意：这里返回False，因为游戏还没有真正开始，只是开始了倒计时
        
        # 如果不满足倒计时条件但有倒计时在进行，则取消倒计时
        if game_id in self.countdown_tasks and not self.countdown_tasks[game_id].done():
            # 检查是否还有足够的非观战者玩家
            if total_non_spectator_players < 2 or not all_non_spectator_ready:
                self.countdown_tasks[game_id].cancel()
                self.countdown_tasks.pop(game_id, None)
                self.game_countdowns.pop(game_id, None)
                logging.info(f"游戏 {game_id} 倒计时已取消：不满足开始条件")
        
        return False

    def set_voluntary_spectator(self, game_id: str, player_id: int) -> bool:
        """
        设置玩家为主动观战者
        
        当玩家在准备阶段选择观战模式时调用此方法。
        观战者不能操作，但拥有全图视野。
        
        Args:
            game_id: 游戏ID
            player_id: 玩家ID
            
        Returns:
            bool: 是否成功设置为主动观战者
        """
        if game_id not in self.games or player_id not in self.games[game_id].players:
            return False
        
        player = self.games[game_id].players[player_id]
        
        # 如果游戏已开始，不允许设置观战模式
        if self.games[game_id].game_started:
            return False
        
        # 如果玩家之前已分配基地，需要先移除基地
        if player.base_position is not None:
            self._remove_player_base(game_id, player_id)
        
        player.set_voluntary_spectator()
        
        # 重新初始化准备状态：观战者不需要准备
        if game_id in self.player_ready_states and player_id in self.player_ready_states[game_id]:
            self.player_ready_states[game_id][player_id] = True  # 观战者视为已准备
        
        logging.info(f"玩家 {player_id} 设置为观战模式，基地已移除")
        return True

    def cancel_voluntary_spectator(self, game_id: str, player_id: int) -> bool:
        """
        取消玩家的主动观战者状态
        
        当玩家在准备阶段选择取消观战模式时调用此方法。
        
        Args:
            game_id: 游戏ID
            player_id: 玩家ID
            
        Returns:
            bool: 是否成功取消观战者状态
        """
        if game_id not in self.games or player_id not in self.games[game_id].players:
            return False
        
        player = self.games[game_id].players[player_id]
        
        # 如果游戏已开始，不允许取消观战模式
        if self.games[game_id].game_started:
            return False
        
        # 重置玩家的观战状态
        player.cancel_voluntary_spectator()
        
        # 为玩家重新分配基地
        self._assign_player_base(game_id, player_id)
        
        # 重新初始化准备状态：取消观战后需要重新准备
        if game_id in self.player_ready_states and player_id in self.player_ready_states[game_id]:
            self.player_ready_states[game_id][player_id] = False  # 取消观战后视为未准备
        
        logging.info(f"玩家 {player_id} 取消观战模式，基地已重新分配")
        return True
    
    def _remove_player_base(self, game_id: str, player_id: int):
        """移除玩家的基地（用于观战模式切换）"""
        if game_id not in self.games:
            return
        
        game_state = self.games[game_id]
        player = game_state.players.get(player_id)
        
        if player is None or player.base_position is None:
            return
        
        base_x, base_y = player.base_position
        
        # 重置基地地形为平原
        base_tile = game_state.tiles[base_y][base_x]
        base_tile.terrain_type = TerrainType.PLAIN
        base_tile.required_soldiers = 0
        base_tile.owner = None
        base_tile.soldiers = 0
        
        # 清除玩家的基地位置
        player.base_position = None
        
        logging.info(f"已移除玩家 {player_id} 的基地")
    
    def _assign_player_base(self, game_id: str, player_id: int):
        """为玩家分配基地（用于取消观战模式）"""
        if game_id not in self.games:
            return
        
        game_state = self.games[game_id]
        player = game_state.players.get(player_id)
        
        if player is None or player.base_position is not None:
            return
        
        # 找到可用的基地位置（选择一个没有基地的spawn point）
        available_positions = []
        for i, (base_x, base_y) in enumerate(game_state.spawn_points):
            # 检查这个位置是否已经有基地
            has_base = False
            for other_player in game_state.players.values():
                if other_player.base_position == (base_x, base_y):
                    has_base = True
                    break
            if not has_base:
                available_positions.append((base_x, base_y))
        
        if not available_positions:
            # 如果没有可用位置，生成新的基地位置
            new_player_count = len(game_state.players) + 1
            game_state.spawn_points = game_state.generate_random_spawn_points(new_player_count, min_distance=10)
            base_x, base_y = game_state.spawn_points[-1]  # 使用最后一个位置
        else:
            # 使用第一个可用位置
            base_x, base_y = available_positions[0]
        
        # 设置玩家的基地位置
        player.base_position = (base_x, base_y)
        
        # 设置基地地形
        base_tile = game_state.tiles[base_y][base_x]
        base_tile.terrain_type = TerrainType.BASE
        base_tile.required_soldiers = base_tile._get_required_soldiers()
        base_tile.owner = player
        base_tile.soldiers = 10
        
        logging.info(f"已为玩家 {player_id} 分配基地位置 ({base_x}, {base_y})")

    def broadcast_player_status_update(self, game_id: str):
        """广播玩家状态更新给房间内所有玩家"""
        if game_id not in self.players:
            return
        
        message = {
            'type': 'player_status_updated',
            'game_state': self.get_game_state(game_id)
        }
        
        for player_id, handler in self.players[game_id].items():
            if handler:
                handler.write_message(json.dumps(message, default=str))

    def broadcast_game_start(self, game_id: str):
        """广播游戏开始消息给所有玩家"""
        if game_id not in self.players:
            return
        
        message = {
            'type': 'game_started',
            'game_state': self.get_game_state(game_id)
        }
        
        for player_id, handler in self.players[game_id].items():
            if handler:
                handler.write_message(json.dumps(message, default=str))
    
    def broadcast_game_reset(self, game_id: str):
        """广播游戏重置消息给所有玩家"""
        if game_id not in self.players:
            return
        
        message = {
            'type': 'game_reset',
            'game_state': self.get_game_state(game_id)
        }
        
        for player_id, handler in self.players[game_id].items():
            if handler:
                handler.write_message(json.dumps(message, default=str))
    
    def broadcast_player_left(self, game_id: str, player_id: int, player_name: str):
        """广播玩家离开消息给其他玩家"""
        if game_id not in self.players:
            return
        
        message = {
            'type': 'player_left',
            'player_id': player_id,
            'player_name': player_name,
            'game_state': self.get_game_state(game_id)
        }
        
        for pid, handler in self.players[game_id].items():
            # 不向离开的玩家发送消息（因为连接已断开）
            if handler and pid != player_id:
                handler.write_message(json.dumps(message, default=str))
    
    def broadcast_game_state(self, game_id: str):
        """向房间内所有玩家广播游戏状态"""
        if game_id not in self.games:
            return
        
        game = self.games[game_id]
        
        # 为每个玩家发送个性化的游戏状态
        for player_id, player in game.players.items():
            if player_id in self.connections[game_id]:
                handler = self.connections[game_id][player_id]
                # 为每个玩家获取个性化的游戏状态（包含战争迷雾）
                personalized_state = self.get_game_state(game_id, player_id)
                response = {
                    'type': 'game_state',
                    'game_state': personalized_state
                }
                try:
                    handler.write_message(json.dumps(response, default=str))
                except Exception as e:
                    print(f"Error sending game state to player {player_id}: {e}")
                    # 连接可能已断开，移除连接
                    self.remove_player_connection(game_id, player_id)
    
    def broadcast_game_over(self, game_id: str):
        """广播游戏结束消息给所有玩家"""
        if game_id not in self.games or game_id not in self.players:
            return
        
        game_state = self.games[game_id]
        
        message = {
            'type': 'game_over',
            'winner': game_state.winner.name if game_state.winner else None,
            'game_state': self.get_game_state(game_id)
        }
        
        for player_id, handler in self.players[game_id].items():
            if handler:
                try:
                    handler.write_message(json.dumps(message, default=str))
                except Exception as e:
                    print(f"Error sending game over message to player {player_id}: {e}")
                    # 连接可能已断开，移除连接
                    self.remove_player_connection(game_id, player_id)
        
        # 发送胜利音效触发消息
        if game_state.winner:
            # 获取胜利者的胜利音乐偏好
            victory_music = 'royal-vict.mp3'  # 默认胜利音乐
            if game_state.winner.id in self.player_user_mapping:
                winner_user_id = self.player_user_mapping[game_state.winner.id]
                user_music_settings = db.get_user_music_settings(winner_user_id)
                victory_music = user_music_settings.get('selected_victory', 'royal-vict.mp3')
            
            victory_message = {
                'type': 'play_victory_sound',
                'winner': game_state.winner.name,
                'winner_id': game_state.winner.id,
                'victory_music': victory_music
            }
            
            for player_id, handler in self.players[game_id].items():
                if handler:
                    try:
                        handler.write_message(json.dumps(victory_message, default=str))
                    except Exception as e:
                        print(f"Error sending victory sound message to player {player_id}: {e}")
                        # 连接可能已断开，移除连接
                        self.remove_player_connection(game_id, player_id)
    
    def move_soldiers(self, game_id: str, player_id: int, from_x: int, from_y: int, to_x: int, to_y: int) -> bool:
        """移动士兵"""
        if game_id not in self.games:
            return False
        
        game_state = self.games[game_id]
        
        # 检查玩家是否为旁观者
        if player_id in game_state.players and game_state.players[player_id].is_spectator:
            return False
        
        return game_state.move_soldiers(from_x, from_y, to_x, to_y, player_id)
    
    def get_game_state(self, game_id: str, player_id: int = None) -> dict:
        """获取游戏状态"""
        if game_id not in self.games:
            return {}
        
        game_state = self.games[game_id]
        
        # 检查是否为旁观者玩家
        is_spectator = False
        if player_id and player_id in game_state.players:
            is_spectator = game_state.players[player_id].is_spectator
        
        # 转换为可序列化的字典
        state_dict = {
            'map_width': game_state.map_width,
            'map_height': game_state.map_height,
            'current_tick': game_state.current_tick,
            'game_over': game_state.game_over,
            'game_started': game_state.game_started,
            'winner': game_state.winner.name if game_state.winner else None,
            'tiles': [],
            'players': {},
            'leaderboard': [],  # 添加排行榜数据
            'movement_arrows': {}  # 添加移动箭头数据（仅当前玩家可见）
        }
        
        # 添加倒计时信息
        if game_id in self.game_countdowns:
            state_dict['countdown'] = self.game_countdowns[game_id]
        else:
            state_dict['countdown'] = 0
        
        # 获取排行榜数据
        state_dict['leaderboard'] = game_state.get_all_players_stats()
        
        # 添加移动箭头数据（仅当前玩家可见）
        if player_id and player_id in game_state.movement_arrows:
            state_dict['movement_arrows'] = game_state.movement_arrows[player_id]
        else:
            state_dict['movement_arrows'] = []
        
        # 序列化地图
        for y in range(game_state.map_height):
            row = []
            for x in range(game_state.map_width):
                tile = game_state.tiles[y][x]
                
                # 如果是旁观者，显示完整地图信息
                if is_spectator:
                    tile_data = {
                        'x': tile.x,
                        'y': tile.y,
                        'terrain_type': tile.terrain_type.value,
                        'owner_id': tile.owner.id if tile.owner else None,
                        'soldiers': tile.soldiers,
                        'required_soldiers': tile.required_soldiers,
                        'is_fog': False  # 旁观者无战争迷雾
                    }
                # 如果指定了玩家ID且该地块对玩家不可见，则隐藏详细信息
                elif player_id and player_id in tile.visibility and not tile.visibility.get(player_id, False):
                    # 对于不可见的地块，显示真实地形信息但隐藏所有者和士兵数量
                    tile_data = {
                        'x': tile.x,
                        'y': tile.y,
                        'terrain_type': tile.terrain_type.value,  # 显示真实地形类型
                        'owner_id': None,
                        'soldiers': 0,
                        'required_soldiers': 0,
                        'is_fog': True  # 标记为战争迷雾区域
                    }
                else:
                    # 对于可见的地块，显示完整信息
                    tile_data = {
                        'x': tile.x,
                        'y': tile.y,
                        'terrain_type': tile.terrain_type.value,
                        'owner_id': tile.owner.id if tile.owner else None,
                        'soldiers': tile.soldiers,
                        'required_soldiers': tile.required_soldiers,
                        'is_fog': False  # 标记为非战争迷雾区域
                    }
                
                row.append(tile_data)
            state_dict['tiles'].append(row)
        
        # 序列化玩家，包含准备状态和旁观者状态
        for pid, player in game_state.players.items():
            state_dict['players'][pid] = {
                'id': player.id,
                'name': player.name,
                'color': player.color,
                'base_position': player.base_position,
                'is_alive': player.is_alive,
                'is_spectator': player.is_spectator,  # 添加旁观者状态
                'voluntary_spectator': player.voluntary_spectator,  # 添加主动观战状态
                'ready': self.player_ready_states.get(game_id, {}).get(pid, False)
            }
        
        return state_dict
    
    def _update_all_games(self):
        """更新所有游戏状态"""
        current_time = time.time()
        games_to_remove = []
        
        for game_id, game_state in self.games.items():
            # 更新游戏逻辑
            game_state.update()
            
            # 检查游戏是否结束
            if game_state.game_over and game_id not in self.game_over_games:
                self.game_over_games.add(game_id)
                
                # 记录游戏开始时间（如果还没有记录）
                if game_id not in self.game_start_times:
                    self.game_start_times[game_id] = current_time
                
                # 计算游戏时长
                game_duration = int(current_time - self.game_start_times[game_id])
                
                # 记录游戏结果
                self._record_game_result(game_id, game_state, game_duration)
                
                # 广播游戏结束消息
                self.broadcast_game_over(game_id)
                
                # 30秒后移除游戏
                games_to_remove.append((game_id, current_time + 30))
            
            # 定期广播游戏状态（每秒一次）
            elif current_time - self.last_broadcast_time.get(game_id, 0) >= 1:
                self.broadcast_game_state(game_id)
                self.last_broadcast_time[game_id] = current_time
        
        # 移除已经结束的游戏
        for game_id, remove_time in games_to_remove:
            if current_time >= remove_time:
                self.close_room(game_id)
    
    def _record_game_result(self, game_id: str, game_state: GameState, game_duration: int):
        """记录游戏结果到数据库"""
        try:
            # 获取胜利者ID
            winner_user_id = None
            if game_state.winner and game_state.winner.id in self.player_user_mapping:
                winner_user_id = self.player_user_mapping[game_state.winner.id]
            
            # 记录游戏
            game_db_id = db.record_game(game_id, winner_user_id, game_duration, game_state.current_tick)
            
            # 记录每个玩家的游戏结果
            for player_id, player in game_state.players.items():
                if player_id in self.player_user_mapping:
                    user_id = self.player_user_mapping[player_id]
                    
                    # 获取玩家排名
                    player_stats = game_state.get_player_stats(player_id)
                    final_rank = player_stats.get('rank', len(game_state.players))
                    
                    # 记录游戏参与者信息
                    db.record_game_player(
                        game_db_id, user_id, final_rank, player.is_alive
                    )
                    
                    # 只在游戏正常结束时更新用户统计
                    if game_state.game_over_type == 'normal':
                        db.update_user_stats(user_id, {
                            'won': player == game_state.winner
                        })
                        
                        # 为胜利者增加一个"旗"作为奖励
                        if player == game_state.winner:
                            db.add_user_flags(user_id, 1)
                            logging.info(f"为胜利者 {player.name} (用户ID: {user_id}) 增加了1个旗")
            
            logging.info(f"游戏 {game_id} 结果已记录到数据库，结束类型: {game_state.game_over_type}")
            
        except Exception as e:
            logging.error(f"记录游戏结果失败: {str(e)}")
    
    def start_game_countdown(self, game_id: str):
        """开始游戏倒计时"""
        # 如果已经在倒计时中，不再重复开始
        if game_id in self.countdown_tasks and not self.countdown_tasks[game_id].done():
            return
        
        # 初始化倒计时为3秒
        self.game_countdowns[game_id] = 3
        
        # 创建倒计时任务
        async def countdown_task():
            try:
                for i in range(3, 0, -1):
                    self.game_countdowns[game_id] = i
                    # 广播倒计时更新
                    self.broadcast_countdown_update(game_id, i)
                    logging.info(f"游戏 {game_id} 倒计时: {i}秒")
                    await asyncio.sleep(1)
                
                # 倒计时结束，开始游戏
                self.game_countdowns[game_id] = 0
                self.start_game(game_id)
                
            except asyncio.CancelledError:
                logging.info(f"游戏 {game_id} 倒计时已取消")
                # 清理倒计时状态
                self.game_countdowns.pop(game_id, None)
                # 广播倒计时取消消息
                self.broadcast_countdown_cancelled(game_id)
                raise
        
        # 启动倒计时任务
        self.countdown_tasks[game_id] = asyncio.create_task(countdown_task())
    
    def start_game(self, game_id: str):
        """正式开始游戏"""
        if game_id not in self.games:
            return
        
        # 设置游戏开始状态
        self.games[game_id].game_started = True
        # 记录游戏开始时间
        import time
        self.game_start_times[game_id] = time.time()
        # 游戏开始时初始化战争迷雾
        self.games[game_id].update_fog_of_war()
        # 广播游戏开始消息
        self.broadcast_game_start(game_id)
        logging.info(f"游戏 {game_id} 开始!")
        
        # 清理倒计时状态
        self.game_countdowns.pop(game_id, None)
        self.countdown_tasks.pop(game_id, None)
    
    def broadcast_countdown_update(self, game_id: str, seconds: int):
        """广播倒计时更新给所有玩家"""
        if game_id not in self.players:
            return
        
        message = {
            'type': 'countdown_update',
            'seconds': seconds,
            'game_state': self.get_game_state(game_id)
        }
        
        for player_id, handler in self.players[game_id].items():
            if handler:
                handler.write_message(json.dumps(message, default=str))
    
    def broadcast_countdown_cancelled(self, game_id: str):
        """广播倒计时取消消息给所有玩家"""
        if game_id not in self.players:
            return
        
        message = {
            'type': 'countdown_cancelled',
            'game_state': self.get_game_state(game_id)
        }
        
        for player_id, handler in self.players[game_id].items():
            if handler:
                handler.write_message(json.dumps(message, default=str))
    
    def close_room(self, room_id: str):
        """关闭房间并清理相关资源"""
        # 取消该房间的倒计时任务（如果存在）
        if room_id in self.countdown_tasks and not self.countdown_tasks[room_id].done():
            self.countdown_tasks[room_id].cancel()
            self.countdown_tasks.pop(room_id, None)
        
        # 清理倒计时状态（如果存在）
        if room_id in self.game_countdowns:
            self.game_countdowns.pop(room_id, None)
        
        # 清理房间颜色使用记录
        if room_id in self.room_colors:
            del self.room_colors[room_id]
        
        if room_id in self.games:
            # 如果游戏正在进行中但未正常结束，标记为非正常结束
            game_state = self.games[room_id]
            if game_state.game_started and not game_state.game_over:
                game_state.set_abnormal_game_over()
                
                # 记录非正常结束的游戏结果
                if room_id in self.game_start_times:
                    import time
                    game_duration = int(time.time() - self.game_start_times[room_id])
                    self._record_game_result(room_id, game_state, game_duration)
                    del self.game_start_times[room_id]
            
            del self.games[room_id]
            logging.info(f"房间 {room_id} 已关闭")
            
            # 将房间号添加到可用房间号集合中
            self.available_room_ids.add(int(room_id))
        
        if room_id in self.players:
            del self.players[room_id]
        
        if room_id in self.connections:
            del self.connections[room_id]
        
        if room_id in self.player_ready_states:
            del self.player_ready_states[room_id]

    def leave_game(self, game_id: str, player_id: int):
        """玩家离开游戏"""
        if game_id in self.games and game_id in self.players:
            # 从玩家连接字典中删除
            if player_id in self.players[game_id]:
                del self.players[game_id][player_id]
            
            # 从准备状态字典中删除
            if game_id in self.player_ready_states and player_id in self.player_ready_states[game_id]:
                del self.player_ready_states[game_id][player_id]
            
            # 从游戏状态中删除玩家
            if game_id in self.games and player_id in self.games[game_id].players:
                player_name = self.games[game_id].players[player_id].name
                self.games[game_id].remove_player(player_id)
                
                # 广播玩家离开消息给其他玩家
                self.broadcast_player_left(game_id, player_id, player_name)
            
            # 如果游戏已经开始且没有足够的玩家，结束游戏
            if (game_id in self.games and 
                self.games[game_id].game_started and 
                len(self.games[game_id].players) < 2):
                # 设置为非正常结束
                self.games[game_id].set_abnormal_game_over()
                
                # 记录非正常结束的游戏结果
                if game_id in self.game_start_times:
                    import time
                    game_duration = int(time.time() - self.game_start_times[game_id])
                    self._record_game_result(game_id, self.games[game_id], game_duration)
                    del self.game_start_times[game_id]
            
            # 如果房间中没有玩家了，关闭房间
            if game_id in self.games and len(self.games[game_id].players) == 0:
                self.close_room(game_id)
    
    def reset_game(self, game_id: str) -> bool:
        """重置游戏状态，保留玩家但重置游戏地图和状态"""
        if game_id not in self.games:
            return False
        
        # 如果游戏正在进行中但未正常结束，标记为非正常结束并记录结果
        game_state = self.games[game_id]
        if game_state.game_started and not game_state.game_over:
            game_state.set_abnormal_game_over()
            
            # 记录非正常结束的游戏结果
            if game_id in self.game_start_times:
                import time
                game_duration = int(time.time() - self.game_start_times[game_id])
                self._record_game_result(game_id, game_state, game_duration)
                del self.game_start_times[game_id]
        
        # 从game_over_games集合中移除游戏ID，以便新游戏可以正常结束并触发胜利音乐
        if game_id in self.game_over_games:
            self.game_over_games.remove(game_id)
        
        # 保存当前玩家信息
        current_players = list(self.games[game_id].players.values())
        
        # 重新分配颜色以避免重复
        # 清理房间的颜色使用记录，让玩家可以重新分配颜色
        if game_id in self.room_colors:
            self.room_colors[game_id].clear()
        
        # 创建新的游戏状态
        new_game_state = GameState()
        
        # 根据实际玩家数量生成随机出生点（设置最小距离6）
        player_count = len(current_players)
        new_game_state.spawn_points = new_game_state.generate_random_spawn_points(player_count, min_distance=6)
        
        # 重新添加玩家到新游戏状态，分配新颜色
        for i, player in enumerate(current_players):
            # 重置玩家状态
            player.is_alive = True
            player.is_spectator = False  # 重置旁观者身份标记
            
            # 重新分配颜色
            # 获取当前房间内所有已使用的颜色
            used_colors = self.room_colors[game_id].copy() if game_id in self.room_colors else set()
            
            # 找出第一个未使用的颜色
            player_color = None
            player_color_name = None
            
            for color_index, color in enumerate(self.player_colors):
                if color not in used_colors:
                    player_color = color
                    player_color_name = self.color_names[color_index]
                    break
            
            # 如果所有颜色都已使用，使用轮询方式
            if player_color is None:
                player_color = self.player_colors[i % len(self.player_colors)]
                player_color_name = self.color_names[i % len(self.color_names)]
            
            # 更新玩家颜色
            player.color = player_color
            
            # 如果玩家名字是颜色名，也更新为对应的颜色名
            if player.name in self.color_names:
                player.name = player_color_name
            
            # 记录这个房间使用了这个颜色
            if game_id not in self.room_colors:
                self.room_colors[game_id] = set()
            self.room_colors[game_id].add(player_color)
            
            # 分配基地位置（观战者不分配基地）
            if not player.voluntary_spectator:  # 只有非观战者才分配基地
                base_x, base_y = new_game_state.spawn_points[i]
                new_game_state.add_player(player, base_x, base_y)
            else:
                # 观战者加入游戏但不分配基地
                new_game_state.add_player_as_spectator(player)
        
        # 替换旧的游戏状态
        self.games[game_id] = new_game_state
        
        # 重置所有玩家的准备状态为False
        for player_id in self.player_ready_states[game_id]:
            self.player_ready_states[game_id][player_id] = False
        
        # 广播游戏重置后的状态给所有玩家
        self.broadcast_game_state(game_id)
        
        return True


class MainHandler(web.RequestHandler):
    """主页面处理器"""
    
    def get(self):
        """提供游戏客户端页面"""
        import os
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            # 设置缓存头，启用浏览器缓存
            self.set_header("Cache-Control", "public, max-age=600")
            self.write(f.read())


class LoginHandler(web.RequestHandler):
    """登录页面处理器"""
    
    def get(self):
        """提供登录页面"""
        import os
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'login.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            # 设置缓存头，启用浏览器缓存
            self.set_header("Cache-Control", "public, max-age=600")
            self.write(f.read())


class ShopPageHandler(web.RequestHandler):
    """商店页面处理器"""
    
    def get(self):
        """提供商店页面"""
        import os
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'shop.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            # 设置缓存头，启用浏览器缓存
            self.set_header("Cache-Control", "public, max-age=600")
            self.write(f.read())


def make_app():
    """创建Tornado应用"""
    game_manager = GameManager()
    
    # 获取项目根目录的绝对路径
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    # 合并认证路由和游戏路由
    routes = [
        (r"/", MainHandler),
        (r"/login", LoginHandler),
        (r"/shop", ShopPageHandler),
        (r"/ws", GameWebSocketHandler, {"game_manager": game_manager}),
        (r"/icons/(.*)", web.StaticFileHandler, {"path": os.path.join(project_root, "icons")}),
        (r"/music/(.*)", web.StaticFileHandler, {"path": os.path.join(project_root, "music")}),
    ]
    
    # 添加认证路由
    routes.extend(auth_routes)
    
    # 启用 Gzip 压缩设置
    settings = {
        "gzip": True,
        "compress_response": True,
        # 只压缩大于1KB的响应，避免压缩小内容反而增加开销
        "gzip_min_size": 1024,
    }
    
    return web.Application(routes, **settings)


def main(port: int = 8888, debug: bool = False, host: str = '0.0.0.0'):
    """主函数"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='FlagWars游戏服务器')
    parser.add_argument('--port', type=int, default=port, help='服务器监听端口 (默认: 8888)')
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    app = make_app()
    server = httpserver.HTTPServer(app)
    server.listen(args.port, address=host)
    
    # 获取本机IP地址
    import socket
    try:
        # 连接到外部地址（不实际发送数据）来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "未知"
    
    logging.info(f"FlagWars服务器启动在 http://localhost:{args.port}")
    logging.info(f"局域网访问地址: http://{local_ip}:{args.port}")
    logging.info("按 Ctrl+C 停止服务器")
    
    try:
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        logging.info("服务器停止")


if __name__ == "__main__":
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='FlagWars游戏服务器')
    parser.add_argument('--port', type=int, default=8888, help='服务器监听端口 (默认: 8888)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务器监听主机 (默认: 0.0.0.0)')
    args = parser.parse_args()
    
    # 调用主函数并传递参数
    main(port=args.port, debug=args.debug, host=args.host)
