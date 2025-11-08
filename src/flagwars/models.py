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
        self.is_spectator = False  # 新增：标记玩家是否为旁观者
        self.ready = False  # 添加ready属性
    
    def eliminate(self):
        """将玩家标记为已淘汰并设置为旁观者"""
        self.is_alive = False
        self.is_spectator = True
    
    def to_dict(self):
        """将玩家信息转换为字典格式"""
        return {
            "player_id": self.id,
            "name": self.name,
            "color": self.color,
            "is_alive": self.is_alive,
            "is_spectator": self.is_spectator,
            "ready": self.ready
        }


class Tile:
    """地图格子类"""
    def __init__(self, x: int, y: int, terrain_type: TerrainType):
        self.x = x
        self.y = y
        self.terrain_type = terrain_type
        self.owner: Optional[Player] = None
        self.soldiers: int = 0
        self.required_soldiers = self._get_required_soldiers()
        # 战争迷雾：记录每个玩家是否可见此地块 {player_id: bool}
        self.visibility: Dict[int, bool] = {}
    
    def _get_required_soldiers(self) -> int:
        """获取占领所需士兵数量"""
        if self.terrain_type == TerrainType.PLAIN:
            return 0  # 平原无需士兵即可占领
        elif self.terrain_type == TerrainType.BASE:
            return 10
        elif self.terrain_type == TerrainType.TOWER:
            import random
            return random.randint(5, 20)  # 塔楼所需士兵数量随机（5~20）
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
    
    def __init__(self):
        self.map_width = 20
        self.map_height = 20
        self.tiles = []
        self.players = {}
        self.current_tick = 0
        self.game_over = False
        self.game_started = False
        self.winner = None
        self.pending_moves = {}  # 存储待处理的移动操作
        self.spawn_points = []  # 存储玩家出生点
        self.game_over_type = None  # 添加游戏结束类型标记：'normal'（正常结束）或 'abnormal'（非正常结束）
        
        # 初始化地图
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
        
        # 生成一些塔楼 - 增加到8个
        towers_placed = 0
        max_attempts = 100  # 最大尝试次数，防止无限循环
        while towers_placed < 8 and max_attempts > 0:
            max_attempts -= 1
            x = random.randint(2, self.map_width - 3)
            y = random.randint(2, self.map_height - 3)
            # 只有在当前位置是平原时才放置塔楼
            if self.tiles[y][x].terrain_type == TerrainType.PLAIN:
                self.tiles[y][x].terrain_type = TerrainType.TOWER
                self.tiles[y][x].required_soldiers = self.tiles[y][x]._get_required_soldiers()
                # 初始化中立地块的士兵数量
                self.tiles[y][x].soldiers = self.tiles[y][x].required_soldiers
                towers_placed += 1
        
        # 生成一些城墙
        walls_placed = 0
        max_attempts = 100
        while walls_placed < 10 and max_attempts > 0:
            max_attempts -= 1
            x = random.randint(1, self.map_width - 2)
            y = random.randint(1, self.map_height - 2)
            # 只有在当前位置是平原时才放置城墙
            if self.tiles[y][x].terrain_type == TerrainType.PLAIN:
                self.tiles[y][x].terrain_type = TerrainType.WALL
                self.tiles[y][x].required_soldiers = self.tiles[y][x]._get_required_soldiers()
                # 初始化中立地块的士兵数量
                self.tiles[y][x].soldiers = self.tiles[y][x].required_soldiers
                walls_placed += 1
        
        # 生成一些山脉 - 增加到12个
        mountains_placed = 0
        max_attempts = 100
        while mountains_placed < 12 and max_attempts > 0:
            max_attempts -= 1
            x = random.randint(1, self.map_width - 2)
            y = random.randint(1, self.map_height - 2)
            # 只有在当前位置是平原时才放置山脉
            if self.tiles[y][x].terrain_type == TerrainType.PLAIN:
                self.tiles[y][x].terrain_type = TerrainType.MOUNTAIN
                self.tiles[y][x].required_soldiers = self.tiles[y][x]._get_required_soldiers()
                # 山脉不可占领，不需要士兵
                mountains_placed += 1
        
        # 生成一些沼泽
        swamps_placed = 0
        max_attempts = 100
        while swamps_placed < 6 and max_attempts > 0:
            max_attempts -= 1
            x = random.randint(1, self.map_width - 2)
            y = random.randint(1, self.map_height - 2)
            # 只有在当前位置是平原时才放置沼泽
            if self.tiles[y][x].terrain_type == TerrainType.PLAIN:
                self.tiles[y][x].terrain_type = TerrainType.SWAMP
                self.tiles[y][x].required_soldiers = self.tiles[y][x]._get_required_soldiers()
                # 沼泽无需士兵即可占领，不需要初始化士兵数量
                swamps_placed += 1
    
    def generate_random_spawn_points(self, num_players: int) -> List[Tuple[int, int]]:
        """生成随机的玩家出生点"""
        import random
        import math
        
        spawn_points = []
        
        # 地图边界，确保出生点不会太靠近边缘
        min_distance_from_edge = 2
        min_distance_between_spawns = max(
            min(self.map_width, self.map_height) // 3,  # 至少是地图最小尺寸的1/3
            5  # 最小距离为5格
        )
        
        # 尝试生成指定数量的出生点
        attempts = 0
        max_attempts = 1000  # 最大尝试次数，防止无限循环
        
        while len(spawn_points) < num_players and attempts < max_attempts:
            attempts += 1
            
            # 生成随机坐标，确保不靠近边缘
            x = random.randint(min_distance_from_edge, self.map_width - 1 - min_distance_from_edge)
            y = random.randint(min_distance_from_edge, self.map_height - 1 - min_distance_from_edge)
            
            # 检查该位置是否适合作为出生点
            if self._is_valid_spawn_point(x, y, spawn_points, min_distance_between_spawns):
                spawn_points.append((x, y))
        
        # 随机打乱出生点顺序，确保公平性
        random.shuffle(spawn_points)
        
        return spawn_points
    
    def _is_valid_spawn_point(self, x: int, y: int, existing_points: List[Tuple[int, int]], min_distance: int) -> bool:
        """检查指定位置是否适合作为出生点"""
        # 检查地形是否适合（必须是平原）
        if self.tiles[y][x].terrain_type != TerrainType.PLAIN:
            return False
        
        # 检查与现有出生点的距离
        for px, py in existing_points:
            # 使用曼哈顿距离
            distance = abs(x - px) + abs(y - py)
            if distance < min_distance:
                return False
        
        # 检查周围是否有太多障碍物
        obstacle_count = 0
        check_radius = 2  # 检查周围2格的范围
        
        for dy in range(-check_radius, check_radius + 1):
            for dx in range(-check_radius, check_radius + 1):
                nx, ny = x + dx, y + dy
                if (0 <= nx < self.map_width and 0 <= ny < self.map_height and
                    self.tiles[ny][nx].terrain_type == TerrainType.MOUNTAIN):
                    obstacle_count += 1
        
        # 如果周围障碍物太多，则不适合作为出生点
        if obstacle_count > check_radius:  # 允许一些障碍物，但不能太多
            return False
        
        return True
    
    def add_player(self, player: Player, base_x: int, base_y: int):
        """添加玩家并设置基地"""
        self.players[player.id] = player
        player.base_position = (base_x, base_y)
        
        # 为新玩家初始化操作队列
        self.pending_moves[player.id] = []
        
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
            
            # 将玩家拥有的所有地块变为中立，但保留兵力
            for row in self.tiles:
                for tile in row:
                    if tile.owner and tile.owner.id == player_id:
                        # 保留兵力，但将所有者设为None，变为中立
                        tile.owner = None
                        # 基地变为普通平原
                        if tile.terrain_type == TerrainType.BASE:
                            tile.terrain_type = TerrainType.PLAIN
                            tile.required_soldiers = 0
            
            # 从玩家字典中删除
            del self.players[player_id]
    
    def update_game_tick(self):
        """更新游戏刻"""
        self.current_tick += 1
        
        # 执行一个待处理的移动操作（如果有的话）
        self._execute_pending_move()
        
        # 生成士兵
        self._generate_soldiers()
        
        # 更新战争迷雾
        self.update_fog_of_war()
        
        # 检查游戏结束条件
        self._check_game_over()
    
    def _execute_pending_move(self):
        """执行所有玩家待处理的移动操作"""
        # 遍历所有玩家的操作队列
        for player_id, moves in self.pending_moves.items():
            # 如果该玩家有待处理的操作
            if moves:
                # 取出第一个操作并执行
                move_data = moves.pop(0)
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
                # 转移被淘汰玩家的所有兵力和地块给占领者
                self.transfer_player_assets(base_owner.id, player_id)
        
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
    
    def update_fog_of_war(self):
        """更新战争迷雾"""
        # 首先将所有地块的可见性重置为False
        for row in self.tiles:
            for tile in row:
                for player_id in self.players:
                    tile.visibility[player_id] = False
        
        # 为每个玩家计算可见范围
        for player_id, player in self.players.items():
            # 找出该玩家拥有的所有地块
            owned_tiles = []
            for row in self.tiles:
                for tile in row:
                    if tile.owner and tile.owner.id == player_id:
                        owned_tiles.append(tile)
            
            # 对于每个拥有的地块，设置周围一定范围为可见
            for tile in owned_tiles:
                self._set_visibility_around_tile(tile, player_id)
    
    def _set_visibility_around_tile(self, center_tile: Tile, player_id: int, vision_range: int = 2):
        """设置指定地块周围的可见范围"""
        for y in range(max(0, center_tile.y - vision_range), 
                      min(self.map_height, center_tile.y + vision_range + 1)):
            for x in range(max(0, center_tile.x - vision_range), 
                          min(self.map_width, center_tile.x + vision_range + 1)):
                # 计算曼哈顿距离
                distance = abs(x - center_tile.x) + abs(y - center_tile.y)
                if distance <= vision_range:
                    self.tiles[y][x].visibility[player_id] = True
    
    def _check_game_over(self):
        """检查游戏是否结束"""
        alive_players = [p for p in self.players.values() if p.is_alive]
        
        if len(alive_players) <= 1:
            self.game_over = True
            self.game_over_type = 'normal'  # 标记为正常结束
            if alive_players:
                self.winner = alive_players[0]
    
    def set_abnormal_game_over(self):
        """设置游戏为非正常结束"""
        self.game_over = True
        self.game_over_type = 'abnormal'  # 标记为非正常结束
        self.winner = None
    
    def get_player_stats(self, player_id: int):
        """获取玩家的统计数据（总兵力和占领地块数量）"""
        total_soldiers = 0
        owned_tiles = 0
        
        for row in self.tiles:
            for tile in row:
                if tile.owner and tile.owner.id == player_id:
                    total_soldiers += tile.soldiers
                    owned_tiles += 1
        
        return {
            'total_soldiers': total_soldiers,
            'owned_tiles': owned_tiles
        }
    
    def transfer_player_assets(self, eliminated_player_id: int, conqueror_player_id: int):
        """
        转移被淘汰玩家的所有兵力和占领地块给占领者
        
        Args:
            eliminated_player_id: 被淘汰玩家的ID
            conqueror_player_id: 占领者玩家的ID
        """
        # 获取被淘汰玩家和占领者
        eliminated_player = self.players.get(eliminated_player_id)
        conqueror_player = self.players.get(conqueror_player_id)
        
        if not eliminated_player or not conqueror_player:
            return
        
        # 转移地块所有权和兵力
        for row in self.tiles:
            for tile in row:
                if tile.owner and tile.owner.id == eliminated_player_id:
                    # 转移地块所有权
                    tile.owner = conqueror_player
                    
                    # 如果是基地，更新占领者的基地位置
                    if tile.terrain_type == TerrainType.BASE:
                        # 清除原占领者的基地位置（如果有）
                        if conqueror_player.base_position:
                            old_base_x, old_base_y = conqueror_player.base_position
                            if 0 <= old_base_x < self.map_width and 0 <= old_base_y < self.map_height:
                                self.tiles[old_base_y][old_base_x].terrain_type = TerrainType.PLAIN
                        
                        # 设置新的基地位置
                        conqueror_player.base_position = (tile.x, tile.y)
        
        # 将被淘汰玩家设置为旁观者
        eliminated_player.eliminate()
        
        # 检查是否只剩一个存活玩家
        alive_players = [p for p in self.players.values() if p.is_alive and not p.is_spectator]
        if len(alive_players) <= 1:
            self.game_over = True
            if alive_players:
                self.winner = alive_players[0].name
    
    def get_all_players_stats(self):
        """获取所有玩家的统计数据，按总兵力排序"""
        players_stats = []
        
        for player_id, player in self.players.items():
            stats = self.get_player_stats(player_id)
            players_stats.append({
                'player_id': player_id,
                'player_name': player.name,
                'player_color': player.color,
                'total_soldiers': stats['total_soldiers'],
                'owned_tiles': stats['owned_tiles'],
                'is_alive': player.is_alive
            })
        
        # 按总兵力降序排序，如果兵力相同则按占领地块数量排序
        players_stats.sort(key=lambda x: (-x['total_soldiers'], -x['owned_tiles']))
        
        return players_stats
    
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
        
        # 将移动操作添加到对应玩家的队列中
        if player_id not in self.pending_moves:
            self.pending_moves[player_id] = []
        
        self.pending_moves[player_id].append({
            'from_x': from_x,
            'from_y': from_y,
            'to_x': to_x,
            'to_y': to_y,
            'player_id': player_id
        })
        
        return True