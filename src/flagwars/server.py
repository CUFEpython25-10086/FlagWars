"""FlagWars游戏服务器 - 基于Tornado"""
import json
import logging
import asyncio
from typing import Dict, Set
from tornado import web, websocket, ioloop, httpserver

from .models import GameState, Player, TerrainType


class GameWebSocketHandler(websocket.WebSocketHandler):
    """WebSocket处理器，处理游戏通信"""
    
    def initialize(self, game_manager):
        self.game_manager = game_manager
        self.player_id = None
        self.game_id = None
    
    def open(self):
        """WebSocket连接建立"""
        logging.info("WebSocket连接建立")
    
    def on_message(self, message):
        """处理客户端消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'join_game':
                self._handle_join_game(data)
            elif message_type == 'player_ready':
                self._handle_player_ready()
            elif message_type == 'move_soldiers':
                self._handle_move_soldiers(data)
            elif message_type == 'get_game_state':
                self._handle_get_game_state()
            
        except json.JSONDecodeError:
            logging.error("JSON解析错误")
            self.send_error("消息格式错误")
    
    def _handle_join_game(self, data):
        """处理加入游戏请求"""
        player_name = data.get('player_name', '玩家')
        player_color = data.get('color', '#FF0000')
        
        # 创建或加入游戏
        game_id, player_id = self.game_manager.create_or_join_game(player_name, player_color)
        
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
            'game_state': self.game_manager.get_game_state(self.game_id)
        }
        self.write_message(json.dumps(response, default=str))
    
    def _handle_get_game_state(self):
        """处理获取游戏状态请求"""
        if not self.game_id:
            self.send_error("请先加入游戏")
            return
        
        response = {
            'type': 'game_state',
            'game_state': self.game_manager.get_game_state(self.game_id)
        }
        self.write_message(json.dumps(response, default=str))
    
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
        self.player_ready_states: Dict[str, Dict[int, bool]] = {}  # 玩家准备状态
        self.next_player_id = 1
        
        # 启动游戏更新循环
        self._start_game_loop()
    
    def _start_game_loop(self):
        """启动游戏更新循环"""
        async def game_loop():
            while True:
                await asyncio.sleep(1)  # 每1秒更新一次
                self.update_all_games()
        
        ioloop.IOLoop.current().add_callback(game_loop)
    
    def create_or_join_game(self, player_name: str, player_color: str) -> tuple:
        """创建或加入游戏"""
        # 简化：只创建一个游戏
        game_id = "default_game"
        
        # 如果游戏已存在且已开始，拒绝新玩家加入
        if game_id in self.games and self.games[game_id].game_started:
            return None, None  # 返回None表示拒绝加入
        
        # 设置玩家基地位置
        base_positions = [(2, 2), (17, 12), (2, 12), (17, 2)]
        
        if game_id not in self.games:
            # 创建新游戏
            game_state = GameState()
            self.games[game_id] = game_state
            self.players[game_id] = {}
            self.player_ready_states[game_id] = {}
            
        # 创建玩家
        player_id = self.next_player_id
        self.next_player_id += 1
        
        player = Player(player_id, player_name, player_color)
        
        # 分配基地位置
        game_state = self.games[game_id]
        base_index = len(self.players[game_id]) % 4
        base_x, base_y = base_positions[base_index]
        
        game_state.add_player(player, base_x, base_y)
        self.player_ready_states[game_id][player_id] = False  # 初始未准备
        
        return game_id, player_id

    def add_player_connection(self, game_id: str, player_id: int, handler):
        """添加玩家连接"""
        if game_id not in self.players:
            self.players[game_id] = {}
        self.players[game_id][player_id] = handler

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
    
    def move_soldiers(self, game_id: str, player_id: int, from_x: int, from_y: int, to_x: int, to_y: int) -> bool:
        """移动士兵"""
        if game_id not in self.games:
            return False
        
        game_state = self.games[game_id]
        return game_state.move_soldiers(from_x, from_y, to_x, to_y, player_id)
    
    def get_game_state(self, game_id: str) -> dict:
        """获取游戏状态"""
        if game_id not in self.games:
            return {}
        
        game_state = self.games[game_id]
        
        # 转换为可序列化的字典
        state_dict = {
            'map_width': game_state.map_width,
            'map_height': game_state.map_height,
            'current_tick': game_state.current_tick,
            'game_over': game_state.game_over,
            'winner': game_state.winner.name if game_state.winner else None,
            'tiles': [],
            'players': {}
        }
        
        # 序列化地图
        for y in range(game_state.map_height):
            row = []
            for x in range(game_state.map_width):
                tile = game_state.tiles[y][x]
                row.append({
                    'x': tile.x,
                    'y': tile.y,
                    'terrain_type': tile.terrain_type.value,
                    'owner_id': tile.owner.id if tile.owner else None,
                    'soldiers': tile.soldiers,
                    'required_soldiers': tile.required_soldiers
                })
            state_dict['tiles'].append(row)
        
        # 序列化玩家，包含准备状态
        for player_id, player in game_state.players.items():
            state_dict['players'][player_id] = {
                'id': player.id,
                'name': player.name,
                'color': player.color,
                'base_position': player.base_position,
                'is_alive': player.is_alive,
                'ready': self.player_ready_states.get(game_id, {}).get(player_id, False)
            }
        
        return state_dict
    
    def update_all_games(self):
        """更新所有游戏状态"""
        for game_id, game_state in self.games.items():
            # 只在游戏开始且未结束时更新游戏状态
            if game_state.game_started and not game_state.game_over:
                game_state.update_game_tick()
    
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
                self.games[game_id].remove_player(player_id)
            
            # 如果游戏已经开始且没有足够的玩家，结束游戏
            if (game_id in self.games and 
                self.games[game_id].game_started and 
                len(self.games[game_id].players) < 2):
                self.games[game_id].game_over = True


class MainHandler(web.RequestHandler):
    """主页面处理器"""
    
    def get(self):
        """提供游戏客户端页面"""
        import os
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            self.write(f.read())


def make_app():
    """创建Tornado应用"""
    game_manager = GameManager()
    
    return web.Application([
        (r"/", MainHandler),
        (r"/ws", GameWebSocketHandler, {"game_manager": game_manager}),
        (r"/static/(.*)", web.StaticFileHandler, {"path": "static"}),
    ])


def main():
    """主函数"""
    logging.basicConfig(level=logging.INFO)
    
    app = make_app()
    server = httpserver.HTTPServer(app)
    server.listen(8888)
    
    logging.info("FlagWars服务器启动在 http://localhost:8888")
    logging.info("按 Ctrl+C 停止服务器")
    
    try:
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        logging.info("服务器停止")


if __name__ == "__main__":
    main()