"""游戏数据模型定义"""
from enum import Enum
from typing import Dict, List, Optional, Tuple


class TerrainType(Enum):
    """地形类型枚举"""
    PLAIN = "plain"  # 平原
    BASE = "base"    # 基地
    TOWER = "tower"  # 塔楼
    WALL = "wall"    # 城墙
    MOUNTAIN = "mountain"  # 山脉
    SWAMP = "swamp"  # 沼泽


class Player:
    """玩家类"""
    def __init__(self, player_id: int, name: str, color: str):
        self.id = player_id
        self.name = name
        self.color = color
        self.base_position: Optional[Tuple[int, int]] = None
        self.is_alive = True


class Tile:
    """地图格子类"""
    def __init__(self, x: int, y: int, terrain_type: TerrainType):
        self.x = x
        self.y = y
        self.terrain_type = terrain_type
        self.owner: Optional[Player] = None
        self.soldiers: int = 0
        self.required_soldiers = self._get_required_soldiers()
    
    def _get_required_soldiers(self) -> int:
        """获取占领所需士兵数量"""
        if self.terrain_type == TerrainType.PLAIN:
            return 1
        elif self.terrain_type == TerrainType.BASE:
            return 10
        elif self.terrain_type == TerrainType.TOWER:
            return 5
        elif self.terrain_type == TerrainType.WALL:
            return 3
        elif self.terrain_type == TerrainType.MOUNTAIN:
            return 999  # 不可占领
        elif self.terrain_type == TerrainType.SWAMP:
            return 1
        return 1
    
    def is_passable(self) -> bool:
        """判断是否可通行"""
        return self.terrain_type not in [TerrainType.WALL, TerrainType.MOUNTAIN]
    
    def can_be_captured(self) -> bool:
        """判断是否可被占领"""
        return self.terrain_type not in [TerrainType.MOUNTAIN]


class GameState:
    """游戏状态类"""
    def __init__(self, map_width: int = 20, map_height: int = 15):
        self.map_width = map_width
        self.map_height = map_height
        self.tiles: List[List[Tile]] = []
        self.players: Dict[int, Player] = {}
        self.current_tick = 0
        self.game_over = False
        self.game_started = False  # 添加游戏开始状态
        self.winner: Optional[Player] = None
        
        # 操作日志队列，每个tick执行一个操作
        self.pending_moves: List[Dict] = []
        
        self._initialize_map()
    
    def _initialize_map(self):
        """初始化地图"""
        # 创建基础平原地图
        for y in range(self.map_height):
            row = []
            for x in range(self.map_width):
                row.append(Tile(x, y, TerrainType.PLAIN))
            self.tiles.append(row)
        
        # 随机生成地形（简化版）
        self._generate_random_terrain()
    
    def _generate_random_terrain(self):
        """随机生成地形"""
        import random
        
        # 生成一些塔楼
        for _ in range(5):
            x = random.randint(2, self.map_width - 3)
            y = random.randint(2, self.map_height - 3)
            self.tiles[y][x].terrain_type = TerrainType.TOWER
        
        # 生成一些城墙
        for _ in range(10):
            x = random.randint(1, self.map_width - 2)
            y = random.randint(1, self.map_height - 2)
            self.tiles[y][x].terrain_type = TerrainType.WALL
        
        # 生成一些山脉
        for _ in range(8):
            x = random.randint(1, self.map_width - 2)
            y = random.randint(1, self.map_height - 2)
            self.tiles[y][x].terrain_type = TerrainType.MOUNTAIN
        
        # 生成一些沼泽
        for _ in range(6):
            x = random.randint(1, self.map_width - 2)
            y = random.randint(1, self.map_height - 2)
            self.tiles[y][x].terrain_type = TerrainType.SWAMP
    
    def add_player(self, player: Player, base_x: int, base_y: int):
        """添加玩家并设置基地"""
        self.players[player.id] = player
        player.base_position = (base_x, base_y)
        
        # 设置基地地形
        base_tile = self.tiles[base_y][base_x]
        base_tile.terrain_type = TerrainType.BASE
        base_tile.owner = player
        base_tile.soldiers = 10
    
    def remove_player(self, player_id: int):
        """移除玩家"""
        if player_id in self.players:
            player = self.players[player_id]
            
            # 清除玩家拥有的所有地块
            for row in self.tiles:
                for tile in row:
                    if tile.owner and tile.owner.id == player_id:
                        tile.owner = None
                        tile.soldiers = 0
            
            # 从玩家字典中删除
            del self.players[player_id]
    
    def update_game_tick(self):
        """更新游戏刻"""
        self.current_tick += 1
        
        # 执行一个待处理的移动操作（如果有的话）
        self._execute_pending_move()
        
        # 生成士兵
        self._generate_soldiers()
        
        # 检查游戏结束条件
        self._check_game_over()
    
    def _execute_pending_move(self):
        """执行一个待处理的移动操作"""
        if not self.pending_moves:
            return
        
        # 取出第一个操作并执行
        move_data = self.pending_moves.pop(0)
        self._process_move(
            move_data['from_x'], move_data['from_y'],
            move_data['to_x'], move_data['to_y'],
            move_data['player_id']
        )
    
    def _process_move(self, from_x: int, from_y: int, to_x: int, to_y: int, player_id: int):
        """处理移动操作（实际执行）"""
        if not (0 <= from_x < self.map_width and 0 <= from_y < self.map_height):
            return False
        if not (0 <= to_x < self.map_width and 0 <= to_y < self.map_height):
            return False
        
        from_tile = self.tiles[from_y][from_x]
        to_tile = self.tiles[to_y][to_x]
        
        # 检查玩家所有权和可通行性
        if from_tile.owner is None or from_tile.owner.id != player_id:
            return False
        if not to_tile.is_passable():
            return False
        
        # 移动士兵（简化：移动所有士兵）
        if from_tile.soldiers > 0:
            # 处理占领逻辑
            if to_tile.owner is None or to_tile.owner.id != player_id:
                # 敌方或中立地块
                if to_tile.soldiers < from_tile.soldiers:
                    # 占领成功
                    was_neutral = to_tile.owner is None  # 检查是否是未占领地块
                    to_tile.owner = from_tile.owner
                    
                    # 移动到未占领地块时至少留下一名士兵
                    if was_neutral:
                        # 未占领地块，至少留下1名士兵
                        to_tile.soldiers = from_tile.soldiers - to_tile.soldiers
                        from_tile.soldiers = 1  # 留下1名士兵
                    else:
                        # 敌方地块，全部移动
                        to_tile.soldiers = from_tile.soldiers - to_tile.soldiers
                        from_tile.soldiers = 0
                else:
                    # 战斗，双方士兵抵消
                    to_tile.soldiers -= from_tile.soldiers
                    from_tile.soldiers = 0
            else:
                # 友方地块，直接移动
                to_tile.soldiers += from_tile.soldiers
                from_tile.soldiers = 0
            
            # 检查是否占领了敌方基地
            if to_tile.terrain_type == TerrainType.BASE and to_tile.owner is not None:
                base_owner = None
                for player in self.players.values():
                    if player.base_position == (to_x, to_y):
                        base_owner = player
                        break
                
                if base_owner and base_owner.id != player_id:
                    base_owner.is_alive = False
            
            return True
        
        return False
    
    def _generate_soldiers(self):
        """根据地形生成士兵"""
        for row in self.tiles:
            for tile in row:
                if tile.owner is not None:
                    if tile.terrain_type == TerrainType.BASE:
                        # 基地每个游戏刻生成一个士兵
                        tile.soldiers += 1
                    elif tile.terrain_type == TerrainType.TOWER:
                        # 塔楼每个游戏刻生成一个士兵
                        tile.soldiers += 1
                    elif tile.terrain_type == TerrainType.PLAIN:
                        # 平原每15个游戏刻生成一个士兵
                        if self.current_tick % 15 == 0:
                            tile.soldiers += 1
                    elif tile.terrain_type == TerrainType.SWAMP:
                        # 沼泽每个游戏刻减少一个士兵
                        tile.soldiers = max(0, tile.soldiers - 1)
    
    def _check_game_over(self):
        """检查游戏是否结束"""
        alive_players = [p for p in self.players.values() if p.is_alive]
        
        if len(alive_players) <= 1:
            self.game_over = True
            if alive_players:
                self.winner = alive_players[0]
    
    def move_soldiers(self, from_x: int, from_y: int, to_x: int, to_y: int, player_id: int):
        """添加移动士兵请求到队列"""
        if not (0 <= from_x < self.map_width and 0 <= from_y < self.map_height):
            return False
        if not (0 <= to_x < self.map_width and 0 <= to_y < self.map_height):
            return False
        
        from_tile = self.tiles[from_y][from_x]
        
        # 检查玩家所有权和可通行性
        if from_tile.owner is None or from_tile.owner.id != player_id:
            return False
        if from_tile.soldiers <= 0:
            return False
        
        to_tile = self.tiles[to_y][to_x]
        if not to_tile.is_passable():
            return False
        
        # 将移动操作添加到队列
        self.pending_moves.append({
            'from_x': from_x,
            'from_y': from_y,
            'to_x': to_x,
            'to_y': to_y,
            'player_id': player_id
        })
        
        return True