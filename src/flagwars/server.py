"""FlagWars游戏服务器 - 基于Tornado"""
import json
import logging
import asyncio
import time
from typing import Dict, Set
from tornado import web, websocket, ioloop, httpserver

from .models import GameState, Player, TerrainType
from .database import db
from .auth import BaseHandler, auth_routes


class GameWebSocketHandler(websocket.WebSocketHandler):
    """WebSocket处理器，处理游戏通信"""
    
    def initialize(self, game_manager):
        self.game_manager = game_manager
        self.player_id = None
        self.game_id = None
        self.user_id = None  # 添加用户ID
    
    def open(self):
        """WebSocket连接建立"""
        logging.info("WebSocket连接建立")
        
        # 检查会话令牌
        session_token = self.get_cookie("session_token")
        if session_token:
            user = db.verify_session(session_token)
            if user:
                self.user_id = user['id']
                logging.info(f"用户 {user['username']} (ID: {user['id']}) 已连接")
            else:
                logging.warning("无效的会话令牌")
        else:
            logging.info("匿名用户连接")
    
    def on_message(self, message):
        """处理客户端消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
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
            elif message_type == 'move_soldiers':
                self._handle_move_soldiers(data)
            elif message_type == 'get_game_state':
                self._handle_get_game_state()
            elif message_type == 'play_again':
                self._handle_play_again()
            
        except json.JSONDecodeError:
            logging.error("JSON解析错误")
            self.send_error("消息格式错误")
    
    def _handle_create_room(self, data):
        """处理创建房间请求"""
        player_name = data.get('player_name', '玩家')
        
        # 如果用户已登录，使用用户名
        if self.user_id:
            user = db.verify_session(self.get_cookie("session_token"))
            if user:
                player_name = user['username']
        
        # 创建新房间
        room_id = self.game_manager.create_room()
        
        # 加入房间
        game_id, player_id, error = self.game_manager.join_room(room_id, player_name, self.user_id)
        
        if error:
            response = {
                'type': 'create_room_failed',
                'message': error
            }
            self.write_message(json.dumps(response))
            self.close()
            return
        
        self.player_id = player_id
        self.game_id = game_id
        
        # 将WebSocket处理器添加到玩家字典
        self.game_manager.add_player_connection(game_id, player_id, self)
        
        # 发送房间创建成功信息
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
    """游戏管理器"""
    
    def __init__(self):
        self.games: Dict[str, GameState] = {}
        self.players: Dict[str, Dict[int, GameWebSocketHandler]] = {}
        self.connections: Dict[str, Dict[int, GameWebSocketHandler]] = {}  # 修复：添加connections属性
        self.player_ready_states: Dict[str, Dict[int, bool]] = {}  # 玩家准备状态
        self.player_user_mapping: Dict[int, int] = {}  # 玩家ID与用户ID的映射
        self.game_start_times: Dict[str, float] = {}  # 游戏开始时间
        self.last_broadcast_time: Dict[str, float] = {}  # 每个游戏的最后广播时间
        self.game_over_games: Set[str] = set()  # 已结束的游戏集合
        self.next_player_id = 1
        self.next_room_id = 1000  # 房间ID从1000开始
        self.available_room_ids = set()  # 已释放的房间号集合
        
        # 预定义的8种玩家颜色
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
        
        # 启动游戏更新循环
        self._start_game_loop()
    
    def _start_game_loop(self):
        """启动游戏更新循环"""
        async def game_loop():
            while True:
                await asyncio.sleep(0.8)  # 每0.8秒更新一次
                self._update_all_games()
        
        ioloop.IOLoop.current().add_callback(game_loop)
    
    def create_room(self) -> str:
        """创建新房间并返回房间ID"""
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
        
        # 按加入顺序分配颜色
        player_index = len(self.players[room_id])
        predefined_colors = ["#FF0000", "#00FF00", "#0000FF", "#DAA520", "#FF00FF", "#00FFFF", "#FFA500", "#800080"]
        color_names = ["Red", "Green", "Blue", "Gold", "Magenta", "Cyan", "Orange", "Purple"]
        player_color = predefined_colors[player_index % len(predefined_colors)]
        
        # 如果玩家使用默认名字"Player"，则改为颜色英文名
        if player_name == "Player":
            player_name = color_names[player_index % len(color_names)]
        
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
            # 根据当前玩家数量+1生成新的出生点
            new_player_count = len(self.players[room_id]) + 1
            game_state.spawn_points = game_state.generate_random_spawn_points(new_player_count)
        
        # 分配出生点
        base_x, base_y = game_state.spawn_points[player_index]
        
        game_state.add_player(player, base_x, base_y)
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
            del self.players[game_id][player_id]
        if game_id in self.connections and player_id in self.connections[game_id]:
            del self.connections[game_id][player_id]

    def set_player_ready(self, game_id: str, player_id: int) -> bool:
        """设置玩家准备状态，返回游戏是否开始"""
        if game_id not in self.player_ready_states or player_id not in self.player_ready_states[game_id]:
            return False
        
        # 切换准备状态
        self.player_ready_states[game_id][player_id] = not self.player_ready_states[game_id][player_id]
        
        # 检查是否所有玩家都准备且至少有2个玩家
        all_players_ready = all(self.player_ready_states[game_id].values())
        total_players = len(self.player_ready_states[game_id])
        
        # 调试信息：打印准备状态
        logging.info(f"游戏 {game_id} 准备状态: 玩家数={total_players}, 所有玩家准备={all_players_ready}, 准备状态={self.player_ready_states[game_id]}")
        
        # 如果至少有2个玩家、所有玩家都准备且游戏未开始，则开始游戏
        if total_players >= 2 and all_players_ready and game_id in self.games and not self.games[game_id].game_started:
            self.games[game_id].game_started = True
            # 记录游戏开始时间
            import time
            self.game_start_times[game_id] = time.time()
            # 游戏开始时初始化战争迷雾
            self.games[game_id].update_fog_of_war()
            # 广播游戏开始消息
            self.broadcast_game_start(game_id)
            logging.info(f"游戏 {game_id} 开始!")
            return True
        
        return False

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
            'leaderboard': []  # 添加排行榜数据
        }
        
        # 获取排行榜数据
        state_dict['leaderboard'] = game_state.get_all_players_stats()
        
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
            
            logging.info(f"游戏 {game_id} 结果已记录到数据库，结束类型: {game_state.game_over_type}")
            
        except Exception as e:
            logging.error(f"记录游戏结果失败: {str(e)}")
    
    def close_room(self, room_id: str):
        """关闭房间并清理相关资源"""
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
        
        # 创建新的游戏状态
        new_game_state = GameState()
        
        # 根据实际玩家数量生成随机出生点
        player_count = len(current_players)
        new_game_state.spawn_points = new_game_state.generate_random_spawn_points(player_count)
        
        # 重新添加玩家到新游戏状态
        for i, player in enumerate(current_players):
            # 重置玩家状态
            player.is_alive = True
            player.is_spectator = False  # 重置旁观者身份标记
            
            # 分配基地位置
            base_x, base_y = new_game_state.spawn_points[i]
            
            # 添加玩家到新游戏状态
            new_game_state.add_player(player, base_x, base_y)
        
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
            self.write(f.read())


class LoginHandler(web.RequestHandler):
    """登录页面处理器"""
    
    def get(self):
        """提供登录页面"""
        import os
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'login.html')
        with open(template_path, 'r', encoding='utf-8') as f:
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
        (r"/ws", GameWebSocketHandler, {"game_manager": game_manager}),
        (r"/static/(.*)", web.StaticFileHandler, {"path": os.path.join(project_root, "static")}),
        (r"/icons/(.*)", web.StaticFileHandler, {"path": os.path.join(project_root, "icons")}),
        (r"/music/(.*)", web.StaticFileHandler, {"path": os.path.join(project_root, "music")}),
    ]
    
    # 添加认证路由
    routes.extend(auth_routes)
    
    return web.Application(routes)


def main():
    """主函数"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='FlagWars游戏服务器')
    parser.add_argument('--port', type=int, default=8888, help='服务器监听端口 (默认: 8888)')
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    app = make_app()
    server = httpserver.HTTPServer(app)
    server.listen(args.port, address='0.0.0.0')
    
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
    main()