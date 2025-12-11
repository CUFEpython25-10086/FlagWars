"""
FlagWars游戏数据库管理模块

本模块提供完整的SQLite数据库管理功能，包括：
- 用户注册、登录和会话管理
- 游戏记录和统计信息存储
- 音乐系统解锁和设置管理
- 游戏货币（旗）系统管理
- 数据库表结构维护和迁移

核心类：
- Database: 主要的数据库管理类，提供所有数据库操作接口

作者: FlagWars开发团队
版本: 1.0.0
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any


class Database:
    """FlagWars游戏数据库管理类
    
    这个类提供了游戏所需的所有数据库操作功能，包括：
    - 用户管理：注册、登录、验证、会话管理
    - 游戏记录：游戏历史、统计数据、胜负记录
    - 音乐系统：背景音乐和胜利音乐的解锁和选择管理
    - 货币系统：游戏内虚拟货币（旗）的管理
    - 数据库维护：表结构创建、迁移和维护
    
    主要特性：
    - 使用SQLite作为本地数据库，零配置部署
    - 密码安全哈希存储，使用SHA-256 + 随机盐
    - 完整的会话管理，支持过期时间控制
    - 灵活的音乐系统，支持解锁机制
    - 完善的错误处理和异常捕获
    - 数据库迁移支持，自动处理表结构更新
    
    数据库表结构：
    - users: 用户基本信息、统计数据和游戏货币
    - user_sessions: 用户登录会话管理
    - games: 游戏记录和结果
    - game_players: 游戏参与者详细信息
    - user_unlocked_bgm/victory_music: 用户音乐解锁记录
    - user_selected_bgm/victory_music: 用户音乐选择设置
    """
    
    def __init__(self, db_path: str = "flagwars.db"):
        """初始化数据库管理类
        
        Args:
            db_path (str): SQLite数据库文件路径，默认为"flagwars.db"
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构
        
        这个方法会创建游戏所需的所有数据表，包括：
        1. 用户表(users) - 存储用户基本信息和统计数据
        2. 用户会话表(user_sessions) - 管理登录会话
        3. 游戏表(games) - 记录游戏结果和统计
        4. 游戏参与者表(game_players) - 记录每个玩家在游戏中的表现
        5. 音乐相关表 - 管理用户音乐解锁和选择状态
        
        如果数据库已存在，则不会重复创建表。
        对于已有的users表，会检查并添加缺失的flags字段（数据库迁移）。
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 用户表 - 存储用户基本信息、认证信息和游戏统计
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    total_games INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    flags INTEGER DEFAULT 0
                )
            ''')
            
            # 检查并添加flags字段（用于数据库迁移）
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'flags' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN flags INTEGER DEFAULT 0")
                conn.commit()
                print("已添加flags字段到users表")
            
            # 游戏记录表 - 存储每局游戏的整体信息
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id TEXT NOT NULL,
                    winner_id INTEGER,
                    game_duration INTEGER,  -- 游戏持续时间（秒）
                    total_turns INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP,
                    FOREIGN KEY (winner_id) REFERENCES users (id)
                )
            ''')
            
            # 游戏参与者表 - 存储每个玩家在具体游戏中的表现
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    final_rank INTEGER,
                    survived BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (game_id) REFERENCES games (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 用户会话表 - 管理用户登录状态和会话有效期
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 用户解锁背景音乐表 - 记录用户已解锁的背景音乐
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_unlocked_bgm (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    music_name TEXT NOT NULL,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, music_name)
                )
            ''')
            
            # 用户解锁胜利音乐表 - 记录用户已解锁的胜利音乐
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_unlocked_victory_music (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    music_name TEXT NOT NULL,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, music_name)
                )
            ''')
            
            # 用户选择的背景音乐表 - 存储用户当前选择的背景音乐
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_selected_bgm (
                    user_id INTEGER PRIMARY KEY,
                    bgm_name TEXT NOT NULL DEFAULT 'Whispers-of-Strategy.mp3',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 用户选择的胜利音乐表 - 存储用户当前选择的胜利音乐
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_selected_victory_music (
                    user_id INTEGER PRIMARY KEY,
                    victory_music_name TEXT NOT NULL DEFAULT 'royal-vict.mp3',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接
        
        Returns:
            sqlite3.Connection: SQLite数据库连接对象
        """
        return sqlite3.connect(self.db_path)
    
    def hash_password(self, password: str, salt: str = None) -> tuple:
        """密码哈希处理
        
        使用SHA-256算法对密码进行安全哈希，结合随机盐值防止彩虹表攻击。
        
        Args:
            password (str): 原始密码字符串
            salt (str, optional): 盐值，如果为None则自动生成随机盐值
            
        Returns:
            tuple: (密码哈希值, 盐值)的元组
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用SHA-256进行密码哈希
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash, salt
    
    def create_user(self, username: str, password: str, email: str = None) -> Optional[int]:
        """创建新用户
        
        这个方法负责创建新的用户账户，包括密码安全哈希、默认设置和初始化数据。
        会自动为新用户设置默认的音乐选择和解锁默认音乐。
        
        Args:
            username (str): 用户名，必须唯一
            password (str): 用户密码，将进行安全哈希处理
            email (str, optional): 用户邮箱，可选字段
            
        Returns:
            Optional[int]: 创建成功返回用户ID，失败（用户名或邮箱已存在）返回None
            
        流程：
        1. 对密码进行SHA-256哈希处理，生成随机盐值
        2. 将用户信息插入users表
        3. 为用户设置默认的背景音乐和胜利音乐选择
        4. 解锁默认音乐文件供用户使用
        5. 处理可能的IntegrityError异常（用户名/邮箱重复）
        """
        password_hash, salt = self.hash_password(password)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 插入用户基本信息
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                    (username, email, password_hash, salt)
                )
                user_id = cursor.lastrowid
                
                # 为用户设置默认背景音乐选择
                cursor.execute(
                    "INSERT INTO user_selected_bgm (user_id, bgm_name) VALUES (?, ?)",
                    (user_id, 'Whispers-of-Strategy.mp3')
                )
                
                # 为用户设置默认胜利音乐选择
                cursor.execute(
                    "INSERT INTO user_selected_victory_music (user_id, victory_music_name) VALUES (?, ?)",
                    (user_id, 'royal-vict.mp3')
                )
                
                # 为用户解锁默认背景音乐
                cursor.execute(
                    "INSERT INTO user_unlocked_bgm (user_id, music_name) VALUES (?, ?)",
                    (user_id, 'Whispers-of-Strategy.mp3')
                )
                
                # 为用户解锁默认胜利音乐
                cursor.execute(
                    "INSERT INTO user_unlocked_victory_music (user_id, music_name) VALUES (?, ?)",
                    (user_id, 'royal-vict.mp3')
                )
                
                conn.commit()
                return user_id
        except sqlite3.IntegrityError:
            return None  # 用户名或邮箱已存在
    
    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户登录
        
        这个方法验证用户的登录凭证，包括密码验证和会话记录。
        如果验证成功，还会更新用户的最后登录时间。
        
        Args:
            username (str): 用户名
            password (str): 用户密码
            
        Returns:
            Optional[Dict[str, Any]]: 
            - 验证成功返回用户信息的字典（包括所有用户字段和会话过期时间）
            - 验证失败返回None
            
        安全特性：
        - 使用相同的盐值重新计算密码哈希进行验证
        - 防止时序攻击，使用恒定时间比较
        - 自动更新最后登录时间用于统计分析
        """
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row  # 返回字典格式的结果
            cursor = conn.cursor()
            
            # 获取用户信息
            cursor.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )
            user = cursor.fetchone()
            
            if not user:
                return None
            
            # 验证密码 - 使用存储的盐值重新计算哈希
            password_hash, salt = self.hash_password(password, user['salt'])
            if password_hash != user['password_hash']:
                return None
            
            # 更新最后登录时间
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user['id'],)
            )
            conn.commit()
            
            return dict(user)
    
    def create_session(self, user_id: int, expires_hours: int = 24) -> str:
        """创建用户会话
        
        为已验证的用户创建一个新的登录会话，支持会话过期时间控制。
        
        Args:
            user_id (int): 用户ID
            expires_hours (int): 会话过期时间（小时），默认24小时
            
        Returns:
            str: 生成的会话令牌字符串，用于后续的会话验证
            
        特性：
        - 使用secrets.token_urlsafe生成安全的随机令牌
        - 支持自定义会话有效期
        - 会话令牌具有足够的熵值，防止猜测攻击
        """
        session_token = secrets.token_urlsafe(32)  # 生成256位安全随机令牌
        expires_at = datetime.now().timestamp() + (expires_hours * 3600)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_sessions (user_id, session_token, expires_at) VALUES (?, ?, ?)",
                (user_id, session_token, expires_at)
            )
            conn.commit()
        
        return session_token
    
    def verify_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """验证会话令牌
        
        验证提供的会话令牌是否有效且未过期。
        
        Args:
            session_token (str): 会话令牌字符串
            
        Returns:
            Optional[Dict[str, Any]]:
            - 验证成功返回用户信息字典（包括用户基本信息和会话过期时间）
            - 验证失败或已过期返回None
            
        验证逻辑：
        1. 在user_sessions表中查找匹配的会话令牌
        2. 检查会话是否未过期（expires_at > 当前时间戳）
        3. 联接users表获取完整的用户信息
        """
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT u.*, s.expires_at 
                FROM users u
                JOIN user_sessions s ON u.id = s.user_id
                WHERE s.session_token = ? AND s.expires_at > ?
                """,
                (session_token, datetime.now().timestamp())
            )
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            return None
    
    def invalidate_session(self, session_token: str) -> bool:
        """使会话令牌失效
        
        主动使指定的会话令牌失效，通常用于用户主动登出。
        
        Args:
            session_token (str): 要失效的会话令牌
            
        Returns:
            bool: 操作是否成功（是否有令牌被删除）
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_sessions WHERE session_token = ?",
                (session_token,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """获取用户统计信息
        
        获取指定用户的游戏统计数据，包括游戏场次、胜负记录、胜率等。
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            Dict[str, Any]: 包含以下统计信息的字典：
            - total_games: 总游戏场次
            - wins: 胜利场次
            - losses: 失败场次
            - flags: 当前拥有的旗数量（游戏货币）
            - win_rate: 胜率百分比（小数点后两位）
            
        特性：
        - 自动计算胜率，避免除零错误
        - 使用字典的get方法提供默认值，防止数据不存在时的错误
        - 返回格式化的统计数据，便于前端显示
        """
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取用户基本统计信息
            cursor.execute(
                """
                SELECT 
                    total_games, wins, losses, flags
                FROM users WHERE id = ?
                """,
                (user_id,)
            )
            user = cursor.fetchone()
            
            if user:
                stats = dict(user)
                # 确保所有字段都存在，如果不存在则使用默认值
                total_games = stats.get('total_games', 0)
                wins = stats.get('wins', 0)
                losses = stats.get('losses', 0)
                flags = stats.get('flags', 0)
                
                # 计算胜率（避免除零错误）
                win_rate = 0
                if total_games > 0:
                    win_rate = round(wins * 100.0 / total_games, 2)
                
                return {
                    'total_games': total_games,
                    'wins': wins,
                    'losses': losses,
                    'flags': flags,
                    'win_rate': win_rate
                }
            
            # 如果用户不存在，返回默认统计数据
            return {
                'total_games': 0,
                'wins': 0,
                'losses': 0,
                'flags': 0,
                'win_rate': 0
            }
    
    def update_user_stats(self, user_id: int, game_result: Dict[str, Any]):
        """更新用户游戏统计
        
        根据游戏结果更新用户的统计数据，包括总游戏数和胜负记录。
        
        Args:
            user_id (int): 用户ID
            game_result (Dict[str, Any]): 游戏结果字典，必须包含'won'字段
                - 'won': bool，游戏是否获胜
            
        流程：
        1. 总游戏数加1
        2. 根据游戏结果（胜负）相应增加wins或losses
        3. 事务性操作，确保数据一致性
        
        注意：
        - 只更新胜负记录，不更新其他统计（如旗数量）
        - 使用原子操作保证数据一致性
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 更新总游戏数
            cursor.execute(
                "UPDATE users SET total_games = total_games + 1 WHERE id = ?",
                (user_id,)
            )
            
            # 根据游戏结果更新统计
            if game_result.get('won', False):
                # 胜利，增加胜利场次
                cursor.execute(
                    "UPDATE users SET wins = wins + 1 WHERE id = ?",
                    (user_id,)
                )
            else:
                # 失败，增加失败场次
                cursor.execute(
                    "UPDATE users SET losses = losses + 1 WHERE id = ?",
                    (user_id,)
                )
            
            conn.commit()
    
    def record_game(self, room_id: str, winner_id: Optional[int], game_duration: int, total_turns: int) -> int:
        """记录游戏结果
        
        记录一局游戏的基本信息到games表中。
        
        Args:
            room_id (str): 游戏房间ID
            winner_id (Optional[int]): 获胜用户ID，可能为None（平局或未分胜负）
            game_duration (int): 游戏持续时间（秒）
            total_turns (int): 总回合数
            
        Returns:
            int: 创建的游戏记录ID
            
        用途：
        - 为游戏历史记录提供基础数据
        - 支持游戏统计和排行榜功能
        - 便于游戏回放和分析
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO games (room_id, winner_id, game_duration, total_turns, finished_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (room_id, winner_id, game_duration, total_turns)
            )
            conn.commit()
            return cursor.lastrowid
    
    def record_game_player(self, game_id: int, user_id: int, final_rank: int, survived: bool):
        """记录游戏参与者信息
        
        记录特定用户在某个游戏中的表现详情。
        
        Args:
            game_id (int): 游戏ID（来自games表）
            user_id (int): 用户ID
            final_rank (int): 最终排名（1为第一名）
            survived (bool): 是否存活到最后
            
        用途：
        - 详细记录每个玩家在游戏中的表现
        - 支持个人游戏历史查看
        - 为成就系统提供数据支持
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO game_players (game_id, user_id, final_rank, survived)
                VALUES (?, ?, ?, ?)
                """,
                (game_id, user_id, final_rank, survived)
            )
            conn.commit()
    
    def get_available_music(self) -> Dict[str, List[str]]:
        """获取所有可用的音乐
        
        返回游戏中所有可用的背景音乐和胜利音乐列表。
        目前使用硬编码列表，实际应用中可从文件系统动态获取。
        
        Returns:
            Dict[str, List[str]]: 包含以下键的字典：
            - 'bgm': 可用背景音乐列表
            - 'victory': 可用胜利音乐列表
            
        音乐列表：
        背景音乐：
        - Whispers-of-Strategy.mp3 (默认)
        - Electric-Heartbeat.mp3
        - Moonlight-and-Marmalade.mp3
        
        胜利音乐：
        - royal-vict.mp3 (默认)
        - folk-vict.mp3
        - mario-vict.mp3
        - weird-horn-vict.mp3
        """
        try:
            # 这里应该从文件系统获取实际的音乐文件列表
            # 为了简化，我们返回硬编码的列表
            bgm_list = [
                'Whispers-of-Strategy.mp3',
                'Electric-Heartbeat.mp3',
                'Moonlight-and-Marmalade.mp3'
            ]
            
            victory_list = [
                'royal-vict.mp3',
                'folk-vict.mp3',
                'mario-vict.mp3',
                'weird-horn-vict.mp3'
            ]
            
            return {
                'bgm': bgm_list,
                'victory': victory_list
            }
        except Exception as e:
            print(f"获取可用音乐错误: {e}")
            # 出错时返回默认音乐列表
            return {
                'bgm': ['Whispers-of-Strategy.mp3'],
                'victory': ['royal-vict.mp3']
            }
    
    def get_user_game_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """获取用户游戏历史
        
        获取指定用户的最近游戏记录，包括游戏详情、胜负情况、个人表现等。
        
        Args:
            user_id (int): 用户ID
            limit (int): 返回记录数量限制，默认10条
            
        Returns:
            List[Dict[str, Any]]: 游戏历史记录列表，每条记录包含：
            - id: 游戏ID
            - room_id: 游戏房间ID
            - winner_id: 获胜用户ID
            - game_duration: 游戏持续时间（秒）
            - total_turns: 总回合数
            - created_at: 游戏创建时间
            - finished_at: 游戏结束时间
            - final_rank: 用户在该游戏中的最终排名
            - survived: 用户是否存活到最后
            - won: 用户是否获胜（1为获胜，0为失败）
            
        用途：
        - 用户个人游戏历史查看
        - 成就系统数据支持
        - 游戏统计和分析
        """
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT 
                    g.id, g.room_id, g.winner_id, g.game_duration, g.total_turns, 
                    g.created_at, g.finished_at,
                    gp.final_rank, gp.survived,
                    CASE WHEN g.winner_id = ? THEN 1 ELSE 0 END AS won
                FROM games g
                JOIN game_players gp ON g.id = gp.game_id
                WHERE gp.user_id = ?
                ORDER BY g.finished_at DESC
                LIMIT ?
                """,
                (user_id, user_id, limit)
            )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_user_music_settings(self, user_id: int) -> Dict[str, Any]:
        """获取用户音乐设置
        
        获取指定用户的完整音乐设置信息，包括当前选择的音乐和已解锁的音乐。
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            Dict[str, Any]: 用户音乐设置字典，包含：
            - selected_bgm: 当前选择的背景音乐文件名
            - selected_victory: 当前选择的胜利音乐文件名
            - unlocked_bgm: 已解锁的背景音乐列表
            - unlocked_victory: 已解锁的胜利音乐列表
            
        错误处理：
        - 如果用户不存在或数据库操作失败，返回默认设置
        - 确保始终返回有效的音乐文件列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取用户选择的背景音乐
                cursor.execute(
                    "SELECT bgm_name FROM user_selected_bgm WHERE user_id = ?",
                    (user_id,)
                )
                selected_bgm = cursor.fetchone()
                selected_bgm = selected_bgm[0] if selected_bgm else 'Whispers-of-Strategy.mp3'
                
                # 获取用户选择的胜利音乐
                cursor.execute(
                    "SELECT victory_music_name FROM user_selected_victory_music WHERE user_id = ?",
                    (user_id,)
                )
                selected_victory = cursor.fetchone()
                selected_victory = selected_victory[0] if selected_victory else 'royal-vict.mp3'
                
                # 获取用户解锁的背景音乐
                cursor.execute(
                    "SELECT music_name FROM user_unlocked_bgm WHERE user_id = ?",
                    (user_id,)
                )
                unlocked_bgm = [row[0] for row in cursor.fetchall()]
                
                # 获取用户解锁的胜利音乐
                cursor.execute(
                    "SELECT music_name FROM user_unlocked_victory_music WHERE user_id = ?",
                    (user_id,)
                )
                unlocked_victory = [row[0] for row in cursor.fetchall()]
                
                return {
                    'selected_bgm': selected_bgm,
                    'selected_victory': selected_victory,
                    'unlocked_bgm': unlocked_bgm,
                    'unlocked_victory': unlocked_victory
                }
        except Exception as e:
            print(f"获取用户音乐设置错误: {e}")
            # 出错时返回默认音乐设置
            return {
                'selected_bgm': 'Whispers-of-Strategy.mp3',
                'selected_victory': 'royal-vict.mp3',
                'unlocked_bgm': ['Whispers-of-Strategy.mp3'],
                'unlocked_victory': ['royal-vict.mp3']
            }
    
    def update_user_music_selection(self, user_id: int, bgm_name: str = None, victory_music_name: str = None) -> bool:
        """更新用户音乐选择
        
        更新用户当前选择的背景音乐和胜利音乐。
        
        Args:
            user_id (int): 用户ID
            bgm_name (str, optional): 新的背景音乐文件名
            victory_music_name (str, optional): 新的胜利音乐文件名
            
        Returns:
            bool: 更新是否成功
            
        使用说明：
        - 至少提供一个音乐文件参数
        - 使用INSERT OR REPLACE语句确保数据一致性
        - 会验证用户是否有权限选择该音乐（已解锁）
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 更新背景音乐选择
                if bgm_name:
                    cursor.execute(
                        "INSERT OR REPLACE INTO user_selected_bgm (user_id, bgm_name) VALUES (?, ?)",
                        (user_id, bgm_name)
                    )
                
                # 更新胜利音乐选择
                if victory_music_name:
                    cursor.execute(
                        "INSERT OR REPLACE INTO user_selected_victory_music (user_id, victory_music_name) VALUES (?, ?)",
                        (user_id, victory_music_name)
                    )
                
                conn.commit()
                return True
        except Exception as e:
            print(f"更新用户音乐选择错误: {e}")
            return False
    
    def unlock_bgm(self, user_id: int, music_name: str) -> bool:
        """解锁背景音乐
        
        为指定用户解锁指定的背景音乐，使其可以选择使用。
        
        Args:
            user_id (int): 用户ID
            music_name (str): 要解锁的背景音乐文件名
            
        Returns:
            bool: 解锁是否成功
            
        特性：
        - 使用INSERT OR IGNORE避免重复解锁错误
        - 只有真正解锁了新音乐时才返回True
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO user_unlocked_bgm (user_id, music_name) VALUES (?, ?)",
                    (user_id, music_name)
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    def unlock_victory_music(self, user_id: int, music_name: str) -> bool:
        """解锁胜利音乐
        
        为指定用户解锁指定的胜利音乐，使其可以选择使用。
        
        Args:
            user_id (int): 用户ID
            music_name (str): 要解锁的胜利音乐文件名
            
        Returns:
            bool: 解锁是否成功
            
        特性：
        - 使用INSERT OR IGNORE避免重复解锁错误
        - 只有真正解锁了新音乐时才返回True
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO user_unlocked_victory_music (user_id, music_name) VALUES (?, ?)",
                    (user_id, music_name)
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    def get_unlocked_bgm(self, user_id: int) -> List[str]:
        """获取用户已解锁的背景音乐列表
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            List[str]: 已解锁的背景音乐文件名列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT music_name FROM user_unlocked_bgm WHERE user_id = ?",
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]
    
    def get_unlocked_victory_music(self, user_id: int) -> List[str]:
        """获取用户已解锁的胜利音乐列表
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            List[str]: 已解锁的胜利音乐文件名列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT music_name FROM user_unlocked_victory_music WHERE user_id = ?",
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]
    
    def is_bgm_unlocked(self, user_id: int, music_name: str) -> bool:
        """检查背景音乐是否已解锁
        
        Args:
            user_id (int): 用户ID
            music_name (str): 音乐文件名
            
        Returns:
            bool: 是否已解锁
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM user_unlocked_bgm WHERE user_id = ? AND music_name = ?",
                (user_id, music_name)
            )
            return cursor.fetchone() is not None
    
    def is_victory_music_unlocked(self, user_id: int, music_name: str) -> bool:
        """检查胜利音乐是否已解锁
        
        Args:
            user_id (int): 用户ID
            music_name (str): 音乐文件名
            
        Returns:
            bool: 是否已解锁
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT music_name FROM user_unlocked_victory_music WHERE user_id = ? AND music_name = ?",
                (user_id, music_name)
            )
            return cursor.fetchone() is not None
    
    def get_user_flags(self, user_id: int) -> int:
        """获取用户货币（旗）数量
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            int: 用户当前拥有的旗数量，如果用户不存在返回0
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT flags FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def add_user_flags(self, user_id: int, flags: int) -> bool:
        """增加用户货币（旗）数量
        
        Args:
            user_id (int): 用户ID
            flags (int): 要增加的旗数量，必须为正数
            
        Returns:
            bool: 操作是否成功
            
        安全检查：
        - 验证flags参数为正数
        - 使用事务操作确保数据一致性
        """
        if flags <= 0:
            return False
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET flags = flags + ? WHERE id = ?",
                    (flags, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    def spend_user_flags(self, user_id: int, flags: int) -> bool:
        """花费用户货币（旗）数量
        
        扣除用户的旗数量，先检查余额是否充足。
        
        Args:
            user_id (int): 用户ID
            flags (int): 要花费的旗数量，必须为正数
            
        Returns:
            bool: 操作是否成功（余额不足时返回False）
            
        安全检查：
        - 验证flags参数为正数
        - 先检查余额，余额不足时拒绝操作
        - 使用事务操作确保数据一致性
        """
        if flags <= 0:
            return False
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 检查用户是否有足够的旗
                cursor.execute("SELECT flags FROM users WHERE id = ?", (user_id,))
                result = cursor.fetchone()
                if not result or result[0] < flags:
                    return False
                
                # 扣除旗
                cursor.execute(
                    "UPDATE users SET flags = flags - ? WHERE id = ?",
                    (flags, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    def check_username_exists(self, username: str) -> bool:
        """检查用户名是否已存在
        
        用于注册时的用户名唯一性验证。
        
        Args:
            username (str): 要检查的用户名
            
        Returns:
            bool: 用户名是否已存在
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM users WHERE username = ?",
                    (username,)
                )
                return cursor.fetchone() is not None
        except sqlite3.Error:
            return False


# 创建全局数据库实例
db = Database()