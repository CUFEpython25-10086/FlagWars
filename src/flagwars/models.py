"""游戏数据模型定义"""
from enum import Enum
from typing import Dict, List, Optional, Tuple
import random
import threading
import time

# 导入AI模块（如果存在）
try:
    from simple_ai import SimpleAI

    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("注意: simple_ai 模块未找到，AI功能将不可用")


class TerrainType(Enum):
    """地形类型枚举"""
    PLAIN = "plain"  # 平原
    BASE = "base"  # 基地
    TOWER = "tower"  # 塔楼
    WALL = "wall"  # 城墙
    MOUNTAIN = "mountain"  # 山脉
    SWAMP = "swamp"  # 沼泽


class Player:
    """玩家类"""

    def __init__(self, player_id: int, name: str, color: str, is_ai: bool = False):
        self.id = player_id
        self.name = name
        self.color = color
        self.is_ai = is_ai  # 是否为AI玩家
        self.ai_controller = None  # AI控制器实例
        self.base_position: Optional[Tuple[int, int]] = None
        self.is_alive = True
        self.is_spectator = False
        self.ready = False

        # AI相关配置
        self.ai_aggression = 0.6 if is_ai else None
        self.ai_think_time = 0.1  # AI思考时间（秒）

    def set_as_ai(self, aggression: float = 0.6):
        """将玩家设置为AI"""
        if AI_AVAILABLE:
            self.is_ai = True
            self.ai_aggression = aggression
            # 延迟初始化AI控制器，需要游戏状态
            print(f"玩家 {self.name} 已设置为AI (攻击性: {aggression})")

    def initialize_ai_controller(self, game_state):
        """初始化AI控制器"""
        if self.is_ai and AI_AVAILABLE:
            from simple_ai import SimpleAI
            self.ai_controller = SimpleAI(player_id=self.id, aggression=self.ai_aggression)
            self.ai_controller.connect_to_game(game_state)
            print(f"AI控制器已初始化: {self.name}")

    def make_ai_decision(self, game_state):
        """让AI做出决策"""
        if self.is_ai and self.ai_controller and self.is_alive:
            try:
                return self.ai_controller.decide_and_act()
            except Exception as e:
                print(f"AI决策出错: {e}")
                return False
        return False

    def eliminate(self):
        """将玩家标记为已淘汰并设置为旁观者"""
        self.is_alive = False
        self.is_spectator = True
        # AI玩家被淘汰时清理资源
        if self.is_ai:
            self.ai_controller = None

    def to_dict(self):
        """将玩家信息转换为字典格式"""
        return {
            "player_id": self.id,
            "name": self.name,
            "color": self.color,
            "is_ai": self.is_ai,
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

    def __init__(self, enable_ai: bool = True, ai_tick_interval: int = 1):
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

        # AI相关设置
        self.enable_ai = enable_ai and AI_AVAILABLE
        self.ai_tick_interval = ai_tick_interval  # AI每隔多少个游戏刻决策一次
        self.ai_decision_lock = threading.Lock()  # AI决策锁，防止竞争条件

        # 初始化地图
        self._initialize_map()

        if self.enable_ai:
            print("AI功能已启用")
        elif not AI_AVAILABLE:
            print("AI功能不可用: simple_ai 模块未找到")

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

    def generate_random_spawn_points(self, num_players: int) -> List[Tuple[int, int]]:
        """
        生成尽可能分散的玩家出生点 (使用最大化最小距离算法)
        """
        import random

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
                    random.randint(0, self.map_width - 1),
                    random.randint(0, self.map_height - 1)
                ))
            return spawn_points

        # 2. 随机选择第一个出生点
        first_spawn = random.choice(candidates)
        spawn_points.append(first_spawn)
        # 从候选列表中移除已选点
        candidates.remove(first_spawn)

        # 3. 为剩余玩家寻找最佳位置
        # 算法：遍历所有候选点，找到那个"离最近的已有出生点距离最远"的点
        while len(spawn_points) < num_players and candidates:
            best_candidate = None
            max_min_distance = -1

            for cand in candidates:
                cand_x, cand_y = cand

                # 计算该候选点到所有已存在出生点的最近距离
                min_dist_to_existing = float('inf')
                for sp_x, sp_y in spawn_points:
                    # 使用曼哈顿距离 (或者欧几里得距离)
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

        if adj_passable < 2:  # 至少有两个方向可以走
            return False

        return True

    def add_player(self, player: Player, base_x: int, base_y: int):
        """添加玩家并设置基地"""
        self.players[player.id] = player
        player.base_position = (base_x, base_y)

        # 为新玩家初始化操作队列
        self.pending_moves[player.id] = []

        # 初始化AI控制器
        if player.is_ai and self.enable_ai:
            player.initialize_ai_controller(self)

        # 设置基地地形
        base_tile = self.tiles[base_y][base_x]
        base_tile.terrain_type = TerrainType.BASE
        base_tile.required_soldiers = base_tile._get_required_soldiers()
        base_tile.owner = player
        base_tile.soldiers = 10

    def add_ai_player(self, name: str = "AI Player", color: str = "red",
                      aggression: float = 0.6) -> Player:
        """
        添加AI玩家

        Args:
            name: AI玩家名称
            color: 玩家颜色
            aggression: 攻击性系数 (0.0-1.0)

        Returns:
            创建的AI玩家对象
        """
        if not self.enable_ai:
            print("AI功能未启用，无法添加AI玩家")
            return None

        # 生成玩家ID
        player_id = max(self.players.keys(), default=0) + 1

        # 创建AI玩家
        ai_player = Player(player_id=player_id, name=name, color=color, is_ai=True)
        ai_player.set_as_ai(aggression)

        # 生成出生点
        spawn_points = self.generate_random_spawn_points(len(self.players) + 1)

        if spawn_points:
            base_x, base_y = spawn_points[0]
            self.add_player(ai_player, base_x, base_y)
            print(f"AI玩家 {name} 已添加到位置 ({base_x}, {base_y})")
        else:
            # 回退到随机位置
            import random
            base_x = random.randint(2, self.map_width - 3)
            base_y = random.randint(2, self.map_height - 3)
            self.add_player(ai_player, base_x, base_y)
            print(f"AI玩家 {name} 已添加到随机位置 ({base_x}, {base_y})")

        return ai_player

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

        # AI决策（每隔一定游戏刻执行一次）
        if self.enable_ai and self.current_tick % self.ai_tick_interval == 0:
            self._make_ai_decisions()

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

    def _make_ai_decisions(self):
        """让所有AI玩家做出决策"""
        if not self.enable_ai:
            return

        with self.ai_decision_lock:  # 防止多个AI同时决策造成竞争
            for player_id, player in self.players.items():
                if player.is_ai and player.is_alive and not player.is_spectator:
                    # AI决策
                    decision_made = player.make_ai_decision(self)

                    # 记录AI决策（调试用）
                    if decision_made and self.current_tick % 50 == 0:
                        stats = self.get_player_stats(player_id)
                        print(f"游戏刻 {self.current_tick}: {player.name} 做出了决策，"
                              f"总兵力: {stats['total_soldiers']}, "
                              f"占领地块: {stats['owned_tiles']}")

    def _check_game_over(self):
        """检查游戏是否结束"""
        alive_players = [p for p in self.players.values() if p.is_alive]

        if len(alive_players) <= 1:
            self.game_over = True
            self.game_over_type = 'normal'  # 标记为正常结束
            if alive_players:
                self.winner = alive_players[0]

                # 打印AI玩家的最终统计
                if self.winner.is_ai:
                    stats = self.get_player_stats(self.winner.id)
                    print(f"🎉 AI玩家 {self.winner.name} 获胜！")
                    print(f"最终统计: 总兵力 {stats['total_soldiers']}, "
                          f"占领地块 {stats['owned_tiles']}")

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

        print(f"玩家 {eliminated_player.name} 被 {conqueror_player.name} 淘汰")

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
                'is_ai': player.is_ai,
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


# 演示代码：如何使用集成了AI的GameState
def demo_ai_integration():
    """演示AI集成功能"""
    print("=== AI集成演示 ===")

    # 创建游戏状态，启用AI
    game_state = GameState(enable_ai=True, ai_tick_interval=2)

    # 添加人类玩家
    human_player = Player(player_id=1, name="人类玩家", color="blue")
    game_state.add_player(human_player, base_x=3, base_y=3)

    # 添加AI玩家（简单方法）
    ai_player1 = game_state.add_ai_player(name="AI玩家1", color="red", aggression=0.7)

    # 添加更多AI玩家（手动方法）
    ai_player2 = Player(player_id=3, name="AI玩家2", color="green", is_ai=True)
    ai_player2.set_as_ai(aggression=0.4)
    game_state.add_player(ai_player2, base_x=15, base_y=15)

    # 开始游戏
    game_state.game_started = True

    print(f"游戏开始！玩家列表:")
    for player_id, player in game_state.players.items():
        print(f"  {player.name} ({'AI' if player.is_ai else '人类'}) - {player.color}")

    # 游戏主循环
    max_ticks = 100
    for tick in range(max_ticks):
        if game_state.game_over:
            print(f"游戏在第 {tick} 游戏刻结束！")
            break

        # 更新游戏状态
        game_state.update()

        # 可以在这里添加人类玩家的输入逻辑

        # 每20个游戏刻打印一次状态
        if tick % 20 == 0:
            print(f"游戏刻 {tick}:")
            stats_list = game_state.get_all_players_stats()
            for stats in stats_list:
                print(f"  {stats['player_name']}: {stats['total_soldiers']}兵, "
                      f"{stats['owned_tiles']}地")

    # 打印最终结果
    if game_state.winner:
        print(f"\n🎮 游戏结束！获胜者: {game_state.winner}")
    else:
        print("\n🎮 游戏结束！平局")


if __name__ == "__main__":
    # 如果直接运行此文件，执行演示
    demo_ai_integration()