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
            return 0  # 平原无需士兵即可占领
        elif self.terrain_type == TerrainType.BASE:
            return 10
        elif self.terrain_type == TerrainType.TOWER:
            return 5
        elif self.terrain_type == TerrainType.WALL:
            return 3
        elif self.terrain_type == TerrainType.MOUNTAIN:
            return 9999  # 不可占领
        elif self.terrain_type == TerrainType.SWAMP:
            return 0  # 沼泽无需士兵即可占领
        return 0
    
    def is_passable(self) -> bool:
        """判断是否可通行"""
        return self.terrain_type not in [TerrainType.MOUNTAIN]# 不是[TerrainType.MOUNTAIN, TerrainType.WALL]
    
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
            self.tiles[y][x].required_soldiers = self.tiles[y][x]._get_required_soldiers()
            # 初始化中立地块的士兵数量
            self.tiles[y][x].soldiers = self.tiles[y][x].required_soldiers
        
        # 生成一些城墙
        for _ in range(10):
            x = random.randint(1, self.map_width - 2)
            y = random.randint(1, self.map_height - 2)
            self.tiles[y][x].terrain_type = TerrainType.WALL
            self.tiles[y][x].required_soldiers = self.tiles[y][x]._get_required_soldiers()
            # 初始化中立地块的士兵数量
            self.tiles[y][x].soldiers = self.tiles[y][x].required_soldiers
        
        # 生成一些山脉
        for _ in range(8):
            x = random.randint(1, self.map_width - 2)
            y = random.randint(1, self.map_height - 2)
            self.tiles[y][x].terrain_type = TerrainType.MOUNTAIN
            self.tiles[y][x].required_soldiers = self.tiles[y][x]._get_required_soldiers()
            # 山脉不可占领，不需要士兵
        
        # 生成一些沼泽
        for _ in range(6):
            x = random.randint(1, self.map_width - 2)
            y = random.randint(1, self.map_height - 2)
            self.tiles[y][x].terrain_type = TerrainType.SWAMP
            self.tiles[y][x].required_soldiers = self.tiles[y][x]._get_required_soldiers()
            # 沼泽无需士兵即可占领，不需要初始化士兵数量
    
    def add_player(self, player: Player, base_x: int, base_y: int):
        """添加玩家并设置基地"""
        self.players[player.id] = player
        player.base_position = (base_x, base_y)
        
        # 设置基地地形
        base_tile = self.tiles[base_y][base_x]
        base_tile.terrain_type = TerrainType.BASE
        base_tile.required_soldiers = base_tile._get_required_soldiers()
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
        # 验证坐标有效性
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
        
        # 移动士兵（必须至少留下1名士兵在原地）
        if from_tile.soldiers <= 1:  # 只有当士兵数量大于1时才能移动
            return False
        
        # 检查是否是敌方基地，如果是，记录原始所有者
        is_enemy_base = False
        base_owner = None
        if to_tile.terrain_type == TerrainType.BASE and to_tile.owner is not None and to_tile.owner.id != player_id:
            is_enemy_base = True
            for player in self.players.values():
                if player.base_position == (to_x, to_y):
                    base_owner = player
                    break
        
        # 计算可以移动的士兵数量（至少留下1名士兵）
        movable_soldiers = from_tile.soldiers - 1
        
        # 统一的占领逻辑
        if to_tile.owner is None or to_tile.owner.id != player_id:
            # 敌方或中立地块
            if to_tile.owner is None:
                # 未占领地块，直接使用地块上实际存在的士兵数量
                effective_soldiers = to_tile.soldiers
                
                # 如果required_soldiers为0，直接占领
                if effective_soldiers == 0:
                    to_tile.owner = from_tile.owner
                    to_tile.soldiers = movable_soldiers
                    # 如果是墙，被占领后变为平原
                    if to_tile.terrain_type == TerrainType.WALL:
                        to_tile.terrain_type = TerrainType.PLAIN
                        to_tile.required_soldiers = 0  # 平原无需士兵即可占领
                elif movable_soldiers > effective_soldiers:
                    # 攻击方士兵数量大于防守方，占领成功
                    to_tile.owner = from_tile.owner
                    to_tile.soldiers = movable_soldiers - effective_soldiers
                    # 如果是墙，被占领后变为平原
                    if to_tile.terrain_type == TerrainType.WALL:
                        to_tile.terrain_type = TerrainType.PLAIN
                        to_tile.required_soldiers = 0  # 平原无需士兵即可占领
                elif movable_soldiers == effective_soldiers:
                    # 双方士兵数量相等，同归于尽，地块变为中立
                    to_tile.owner = None
                    to_tile.soldiers = 0
                else:
                    # 攻击方士兵数量小于防守方，防守方获胜
                    # 保存剩余的中立士兵数量，而不是重置为required_soldiers
                    to_tile.owner = None
                    to_tile.soldiers = effective_soldiers - movable_soldiers
            else:
                # 敌方地块
                if movable_soldiers > to_tile.soldiers:
                    # 攻击方士兵数量大于防守方，占领成功
                    to_tile.owner = from_tile.owner
                    to_tile.soldiers = movable_soldiers - to_tile.soldiers
                elif movable_soldiers == to_tile.soldiers:
                    # 双方士兵数量相等，同归于尽，地块变为中立
                    to_tile.owner = None
                    to_tile.soldiers = 0
                else:
                    # 攻击方士兵数量小于防守方，防守方获胜
                    to_tile.soldiers -= movable_soldiers
            
            # 原地留下1名士兵
            from_tile.soldiers = 1
        else:
            # 友方地块，移动可移动的士兵
            to_tile.soldiers += movable_soldiers
            from_tile.soldiers = 1
        
        # 检查是否占领了敌方基地（在士兵抵消后检查）
        if is_enemy_base and base_owner:
            # 只有当当前地块的所有者是攻击方时，才算占领成功
            if to_tile.owner is not None and to_tile.owner.id == player_id:
                base_owner.is_alive = False
        
        return True
    
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