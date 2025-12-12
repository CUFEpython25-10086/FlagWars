"""
游戏数据模型定义 - FlagWars核心数据结构

该模块定义了FlagWars多人夺旗游戏的所有核心数据模型，包括：
1. TerrainType: 游戏地图上的地形类型枚举
2. Player: 玩家数据模型和状态管理
3. Tile: 地图格子模型，包含地形、所有权和可视性
4. GameState: 游戏整体状态管理，包含地图、玩家和游戏逻辑

这些模型类是游戏服务器和客户端之间数据交换的基础，
确保了游戏状态的一致性和可预测性。

作者: FlagWars开发团队
版本: 1.0.0
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
import random # 确保导入random


class TerrainType(Enum):
    """
    游戏地图地形类型枚举
    
    定义了FlagWars游戏地图上所有可能的地形类型。
    不同地形具有不同的属性和游戏机制：
    - 通行性：是否允许玩家单位通过
    - 可占领性：是否可以被玩家占领
    - 防御要求：占领该地形需要的士兵数量
    - 视觉效果：客户端渲染时的颜色和样式
    
    地形分布策略：
    - 平原作为基础地形，覆盖大部分地图
    - 特殊地形随机生成，增加游戏策略性
    - 地形之间保持合理间距，避免完全阻塞
    
    属性:
        PLAIN: 平原 - 可通行，无占领要求，绿色
        BASE: 基地 - 可通行，需10士兵，棕色（玩家出生点）
        TOWER: 塔楼 - 可通行，需5-20随机士兵，灰色（高价值目标）
        WALL: 城墙 - 可通行，需3士兵，深灰色（防御性地形）
        MOUNTAIN: 山脉 - 不可通行，不可占领，深棕色（天然屏障）
        SWAMP: 沼泽 - 可通行，无占领要求，黑色（低价值区域）
    """
    PLAIN = "plain"  # 平原
    BASE = "base"    # 基地
    TOWER = "tower"  # 塔楼
    WALL = "wall"    # 城墙
    MOUNTAIN = "mountain"  # 山脉
    SWAMP = "swamp"  # 沼泽


class Player:
    """
    玩家数据模型类
    
    该类封装了FlagWars游戏中玩家的所有核心属性和状态信息。
    每个玩家实例代表游戏中的一个参与者，可以是人类玩家或AI。
    
    玩家生命周期：
    1. 创建 - 加入游戏时创建Player实例
    2. 游戏中 - 正常参与游戏，可以移动和占领地块
    3. 观战模式 - 主动选择观战，只能观看不能操作
    4. 被淘汰 - 失去所有地块后转为旁观者状态
    5. 结算 - 游戏结束时记录成绩
    
    状态管理：
    - 存活状态：is_alive控制玩家是否仍在游戏中
    - 主动观战：voluntary_spectator控制玩家是否主动选择观战
    - 被动旁观：is_spectator控制玩家是否在观看其他玩家游戏（包含被淘汰和主动观战）
    - 准备状态：ready控制玩家是否准备好开始游戏
    - 基地位置：base_position记录玩家出生点坐标
    
    标识系统：
    - player_id：游戏内唯一标识符（由GameManager分配）
    - name：玩家显示名称（可自定义）
    - color：玩家颜色标识（用于区分不同玩家）
    
    属性:
        id: 玩家在游戏中的唯一标识符
        name: 玩家显示名称
        color: 玩家颜色标识（十六进制颜色码）
        base_position: 玩家基地位置坐标 (x, y)
        is_alive: 玩家是否仍然存活
        voluntary_spectator: 玩家是否主动选择观战模式
        is_spectator: 玩家是否为旁观者（包含主动观战和被淘汰）
        ready: 玩家是否准备好开始游戏
    """
    
    def __init__(self, player_id: int, name: str, color: str) -> None:
        """
        初始化玩家实例
        
        Args:
            player_id: 玩家在游戏中的唯一标识符
            name: 玩家显示名称
            color: 玩家颜色标识（十六进制颜色码，如"#FF0000"）
        """
        self.id = player_id
        self.name = name
        self.color = color
        self.base_position: Optional[Tuple[int, int]] = None
        self.is_alive = True  # 默认存活状态
        self.voluntary_spectator = False  # 默认非主动观战
        self.is_spectator = False  # 默认非旁观者
        self.ready = False  # 默认未准备
    
    def set_voluntary_spectator(self) -> None:
        """
        将玩家设置为主动观战者
        
        当玩家在准备阶段选择观战模式时调用此方法。
        观战者只能观看游戏，不能进行任何操作，但拥有全图视野。
        
        副作用:
            - 设置 voluntary_spectator = True
            - 设置 is_spectator = True
        
        Note:
            该方法通常在玩家准备阶段选择观战模式时调用
        """
        self.voluntary_spectator = True
        self.is_spectator = True
    
    def cancel_voluntary_spectator(self) -> None:
        """
        取消玩家的主动观战者状态
        
        当玩家在准备阶段选择取消观战模式时调用此方法。
        
        副作用:
            - 设置 voluntary_spectator = False
            - 设置 is_spectator = False（仅当玩家还存活时）
        
        Note:
            该方法通常在玩家准备阶段取消观战模式时调用
        """
        self.voluntary_spectator = False
        # 只有当玩家还存活时，才取消旁观者状态（如果已被淘汰则保持旁观状态）
        if self.is_alive:
            self.is_spectator = False
    
    def eliminate(self) -> None:
        """
        将玩家标记为已淘汰
        
        当玩家失去所有地块时调用此方法，将其状态从存活转为淘汰。
        淘汰的玩家会进入旁观者模式，但仍可以观看其他玩家的游戏。
        
        副作用:
            - 设置 is_alive = False
            - 设置 is_spectator = True（但不影响主动观战状态）
        
        Note:
            该方法通常在游戏逻辑检测到玩家无地块时自动调用
        """
        self.is_alive = False
        self.is_spectator = True
    
    def to_dict(self) -> Dict[str, any]:
        """
        将玩家信息转换为字典格式
        
        用于序列化玩家数据，通常用于：
        1. 向客户端发送玩家状态更新
        2. 保存游戏状态到数据库
        3. 游戏结束时的成绩记录
        
        Returns:
            Dict[str, any]: 包含玩家信息的字典
                - player_id: 玩家ID
                - name: 玩家名称
                - color: 玩家颜色
                - is_alive: 是否存活
                - voluntary_spectator: 是否为主动观战者
                - is_spectator: 是否为旁观者（包含主动观战和被淘汰）
                - ready: 是否准备好
        """
        return {
            "player_id": self.id,
            "name": self.name,
            "color": self.color,
            "is_alive": self.is_alive,
            "voluntary_spectator": self.voluntary_spectator,
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
            return 0
        elif self.terrain_type == TerrainType.BASE:
            return 10
        elif self.terrain_type == TerrainType.TOWER:
            import random
            return random.randint(5, 20)
        elif self.terrain_type == TerrainType.WALL:
            return 3
        elif self.terrain_type == TerrainType.MOUNTAIN:
            return 9999
        elif self.terrain_type == TerrainType.SWAMP:
            return 0
        return 0
    
    def is_passable(self) -> bool:
        """判断是否可通行"""
        return self.terrain_type not in [TerrainType.MOUNTAIN]
    
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
        self.pending_moves = {}
        self.spawn_points = []
        self.game_over_type = None
        
        # 添加移动箭头追踪
        self.movement_arrows = {}  # {player_id: [{from_x, from_y, to_x, to_y, created_tick, move_id}]}
        
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
        
        # 随机生成地形
        self._generate_random_terrain()
    
    def _generate_random_terrain(self):
        """随机生成地形"""
        import random
        
        # 生成一些塔楼
        towers_placed = 0
        max_attempts = 100
        while towers_placed < 8 and max_attempts > 0:
            max_attempts -= 1
            x = random.randint(2, self.map_width - 3)
            y = random.randint(2, self.map_height - 3)
            if self.tiles[y][x].terrain_type == TerrainType.PLAIN:
                self.tiles[y][x].terrain_type = TerrainType.TOWER
                self.tiles[y][x].required_soldiers = self.tiles[y][x]._get_required_soldiers()
                self.tiles[y][x].soldiers = self.tiles[y][x].required_soldiers
                towers_placed += 1
        
        # 生成一些城墙
        walls_placed = 0
        max_attempts = 100
        while walls_placed < 10 and max_attempts > 0:
            max_attempts -= 1
            x = random.randint(1, self.map_width - 2)
            y = random.randint(1, self.map_height - 2)
            if self.tiles[y][x].terrain_type == TerrainType.PLAIN:
                self.tiles[y][x].terrain_type = TerrainType.WALL
                self.tiles[y][x].required_soldiers = self.tiles[y][x]._get_required_soldiers()
                self.tiles[y][x].soldiers = self.tiles[y][x].required_soldiers
                walls_placed += 1
        
        # 生成一些山脉
        mountains_placed = 0
        max_attempts = 100
        while mountains_placed < 12 and max_attempts > 0:
            max_attempts -= 1
            x = random.randint(1, self.map_width - 2)
            y = random.randint(1, self.map_height - 2)
            if self.tiles[y][x].terrain_type == TerrainType.PLAIN:
                self.tiles[y][x].terrain_type = TerrainType.MOUNTAIN
                self.tiles[y][x].required_soldiers = self.tiles[y][x]._get_required_soldiers()
                mountains_placed += 1
        
        # 生成一些沼泽
        swamps_placed = 0
        max_attempts = 100
        while swamps_placed < 6 and max_attempts > 0:
            max_attempts -= 1
            x = random.randint(1, self.map_width - 2)
            y = random.randint(1, self.map_height - 2)
            if self.tiles[y][x].terrain_type == TerrainType.PLAIN:
                self.tiles[y][x].terrain_type = TerrainType.SWAMP
                self.tiles[y][x].required_soldiers = self.tiles[y][x]._get_required_soldiers()
                swamps_placed += 1
    
    def generate_random_spawn_points(self, num_players: int, min_distance: int = None) -> List[Tuple[int, int]]:
        """
        生成尽可能分散的玩家出生点 (使用最大化最小距离算法)
        
        Args:
            num_players: 玩家数量
            min_distance: 最小出生距离，如果为None则自动计算
        """
        
        # 如果没有指定最小距离，根据地图大小自动计算
        if min_distance is None:
            # 地图对角线长度的一半作为最小距离，确保分布相对均匀
            map_diagonal = (self.map_width ** 2 + self.map_height ** 2) ** 0.5
            min_distance = max(3, int(map_diagonal / (2 * (num_players ** 0.5))))
        
        spawn_points = []
        candidates = []
        min_distance_from_edge = 2
        
        # 1. 收集所有合法的候选位置
        for y in range(min_distance_from_edge, self.map_height - min_distance_from_edge):
            for x in range(min_distance_from_edge, self.map_width - min_distance_from_edge):
                if self._is_safe_spawn_location(x, y):
                    candidates.append((x, y))
        
        if not candidates:
            # 极端情况：没有候选点，回退到纯随机
            print("Warning: No valid spawn candidates found!")
            for _ in range(num_players):
                spawn_points.append((
                    random.randint(0, self.map_width-1),
                    random.randint(0, self.map_height-1)
                ))
            return spawn_points

        # 2. 随机选择第一个出生点
        first_spawn = random.choice(candidates)
        spawn_points.append(first_spawn)
        # 从候选列表中移除已选点
        candidates.remove(first_spawn)
        
        # 3. 为剩余玩家寻找最佳位置（满足最小距离要求）
        attempts_without_improvement = 0
        max_attempts = 1000
        
        while len(spawn_points) < num_players and candidates and attempts_without_improvement < max_attempts:
            max_attempts -= 1
            best_candidate = None
            max_min_distance = -1
            
            for cand in candidates:
                cand_x, cand_y = cand
                
                # 检查是否满足最小距离要求
                min_dist_to_existing = float('inf')
                for sp_x, sp_y in spawn_points:
                    # 使用曼哈顿距离
                    dist = abs(cand_x - sp_x) + abs(cand_y - sp_y)
                    if dist < min_dist_to_existing:
                        min_dist_to_existing = dist
                
                # 只有当满足最小距离要求时才考虑这个候选点
                if min_dist_to_existing >= min_distance:
                    # 在满足最小距离的点中，选择距离现有出生点最远的
                    if min_dist_to_existing > max_min_distance:
                        max_min_distance = min_dist_to_existing
                        best_candidate = cand
            
            # 如果找到了满足最小距离要求的候选点
            if best_candidate:
                spawn_points.append(best_candidate)
                candidates.remove(best_candidate)
                attempts_without_improvement = 0
            else:
                # 没有找到满足最小距离要求的点，尝试放宽要求
                attempts_without_improvement += 1
                if attempts_without_improvement >= 10:  # 尝试10次后放宽要求
                    min_distance = max(2, min_distance - 1)  # 最小距离减1，但不能小于2
                    attempts_without_improvement = 0
                    print(f"Warning: Reducing min_distance to {min_distance} to find valid spawn points")
        
        # 如果仍然找不到足够的满足条件的点，回退到原有算法
        while len(spawn_points) < num_players and candidates:
            best_candidate = None
            max_min_distance = -1
            
            for cand in candidates:
                cand_x, cand_y = cand
                
                # 计算该候选点到所有已存在出生点的最近距离
                min_dist_to_existing = float('inf')
                for sp_x, sp_y in spawn_points:
                    # 使用曼哈顿距离
                    dist = abs(cand_x - sp_x) + abs(cand_y - sp_y)
                    if dist < min_dist_to_existing:
                        min_dist_to_existing = dist
                
                # 记录"最近距离"最大的那个候选点
                if min_dist_to_existing > max_min_distance:
                    max_min_distance = min_dist_to_existing
                    best_candidate = cand
            
            if best_candidate:
                spawn_points.append(best_candidate)
                candidates.remove(best_candidate)
            else:
                break
        
        # 随机打乱出生点分配顺序，避免第一个生成的点总是被特定玩家占据
        random.shuffle(spawn_points)
        
        return spawn_points

    def _is_safe_spawn_location(self, x: int, y: int) -> bool:
        """检查指定位置的地形和周围环境是否适合作为出生点"""
        # 1. 检查本身地形
        if self.tiles[y][x].terrain_type != TerrainType.PLAIN:
            return False
        
        # 2. 检查周围是否有太多障碍物 (防止出生即被困)
        obstacle_count = 0
        check_radius = 2  # 检查周围2格的范围
        total_neighbors = 0
        
        for dy in range(-check_radius, check_radius + 1):
            for dx in range(-check_radius, check_radius + 1):
                # 跳过中心点
                if dx == 0 and dy == 0:
                    continue
                    
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.map_width and 0 <= ny < self.map_height:
                    total_neighbors += 1
                    # 山脉视为绝对障碍
                    if self.tiles[ny][nx].terrain_type == TerrainType.MOUNTAIN:
                        obstacle_count += 1
        
        # 如果周围超过一半是障碍物，或者紧邻的上下左右有2个以上障碍物，则不安全
        if obstacle_count > (total_neighbors // 2): 
            return False
            
        # 额外检查：确保紧邻的十字方向至少有2个通路
        adj_passable = 0
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.map_width and 0 <= ny < self.map_height:
                if self.tiles[ny][nx].is_passable():
                    adj_passable += 1
        
        if adj_passable < 2: # 至少有两个方向可以走
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
    
    def add_player_as_spectator(self, player: Player):
        """添加观战者玩家（不分配基地）"""
        self.players[player.id] = player
        player.base_position = None  # 观战者没有基地位置
        
        # 为观战者初始化操作队列（虽然他们不会使用）
        self.pending_moves[player.id] = []
        
        # 观战者不分配基地地形
    
    def remove_player(self, player_id: int):
        """移除玩家"""
        if player_id in self.players:
            #player = self.players[player_id]
            
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
    
    def update(self):
        """更新游戏状态（供服务器调用）"""
        # 只有在游戏已经开始且未结束时才更新
        if self.game_started and not self.game_over:
            self.update_game_tick()
    
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
                
                # 使用相同的逻辑生成move_id（在move_soldiers中使用的逻辑）
                move_id = f"{player_id}_{move_data['from_x']}_{move_data['from_y']}_{move_data['to_x']}_{move_data['to_y']}_{move_data.get('created_tick', self.current_tick)}"
                move_data['move_id'] = move_id
                
                success = self._process_move(
                    move_data['from_x'], move_data['from_y'],
                    move_data['to_x'], move_data['to_y'],
                    move_data['player_id']
                )
                # 移动成功后，只清除与这次移动相关的箭头
                if success and player_id in self.movement_arrows:
                    # 只清除与这次具体移动相关的箭头（通过move_id匹配）
                    self._remove_specific_arrow(player_id, move_id)
    
    def _remove_specific_arrow(self, player_id: int, move_id: str):
        """移除与具体移动操作相关的箭头"""
        if player_id not in self.movement_arrows:
            return
        
        arrows = self.movement_arrows[player_id]
        # 找到并移除匹配move_id的箭头
        self.movement_arrows[player_id] = [
            arrow for arrow in arrows 
            if arrow.get('move_id') != move_id
        ]
    
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
            'player_id': player_id,
            'created_tick': self.current_tick
        })
        
        # 添加移动箭头（仅对己方可见）
        if player_id not in self.movement_arrows:
            self.movement_arrows[player_id] = []
        
        # 为这个移动操作生成唯一ID
        move_id = f"{player_id}_{from_x}_{from_y}_{to_x}_{to_y}_{self.current_tick}"
        
        self.movement_arrows[player_id].append({
            'from_x': from_x,
            'from_y': from_y,
            'to_x': to_x,
            'to_y': to_y,
            'created_tick': self.current_tick,
            'move_id': move_id
        })
        
        return True