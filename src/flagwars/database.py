"""数据库模型定义"""
import sqlite3
import hashlib
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any


class Database:
    """数据库管理类"""
    
    def __init__(self, db_path: str = "flagwars.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 用户表
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
                    total_soldiers_killed INTEGER DEFAULT 0,
                    total_tiles_captured INTEGER DEFAULT 0
                )
            ''')
            
            # 游戏记录表
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
            
            # 游戏参与者表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    final_rank INTEGER,
                    soldiers_killed INTEGER DEFAULT 0,
                    tiles_captured INTEGER DEFAULT 0,
                    survived BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (game_id) REFERENCES games (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 用户会话表
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
            
            conn.commit()
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def hash_password(self, password: str, salt: str = None) -> tuple:
        """密码哈希处理"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用SHA-256进行密码哈希
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash, salt
    
    def create_user(self, username: str, password: str, email: str = None) -> Optional[int]:
        """创建新用户"""
        password_hash, salt = self.hash_password(password)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                    (username, email, password_hash, salt)
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None  # 用户名或邮箱已存在
    
    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户登录"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )
            user = cursor.fetchone()
            
            if not user:
                return None
            
            # 验证密码
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
        """创建用户会话"""
        session_token = secrets.token_urlsafe(32)
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
        """验证会话令牌"""
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
        """使会话令牌失效"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_sessions WHERE session_token = ?",
                (session_token,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户统计信息"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT 
                    total_games, wins, losses, 
                    total_soldiers_killed, total_tiles_captured,
                    CASE WHEN total_games > 0 THEN ROUND(wins * 100.0 / total_games, 2) ELSE 0 END AS win_rate
                FROM users WHERE id = ?
                """,
                (user_id,)
            )
            user = cursor.fetchone()
            
            if user:
                return dict(user)
            return None
    
    def update_user_stats(self, user_id: int, game_result: Dict[str, Any]):
        """更新用户游戏统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 更新总游戏数
            cursor.execute(
                "UPDATE users SET total_games = total_games + 1 WHERE id = ?",
                (user_id,)
            )
            
            # 根据游戏结果更新统计
            if game_result.get('won', False):
                cursor.execute(
                    "UPDATE users SET wins = wins + 1 WHERE id = ?",
                    (user_id,)
                )
            else:
                cursor.execute(
                    "UPDATE users SET losses = losses + 1 WHERE id = ?",
                    (user_id,)
                )
            
            # 更新击杀士兵数和占领地块数
            if 'soldiers_killed' in game_result:
                cursor.execute(
                    "UPDATE users SET total_soldiers_killed = total_soldiers_killed + ? WHERE id = ?",
                    (game_result['soldiers_killed'], user_id)
                )
            
            if 'tiles_captured' in game_result:
                cursor.execute(
                    "UPDATE users SET total_tiles_captured = total_tiles_captured + ? WHERE id = ?",
                    (game_result['tiles_captured'], user_id)
                )
            
            conn.commit()
    
    def record_game(self, room_id: str, winner_id: Optional[int], game_duration: int, total_turns: int) -> int:
        """记录游戏结果"""
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
    
    def record_game_player(self, game_id: int, user_id: int, final_rank: int, 
                          soldiers_killed: int, tiles_captured: int, survived: bool):
        """记录游戏参与者信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO game_players (game_id, user_id, final_rank, soldiers_killed, tiles_captured, survived)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (game_id, user_id, final_rank, soldiers_killed, tiles_captured, survived)
            )
            conn.commit()
    
    def get_user_game_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """获取用户游戏历史"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT 
                    g.id, g.room_id, g.winner_id, g.game_duration, g.total_turns, 
                    g.created_at, g.finished_at,
                    gp.final_rank, gp.soldiers_killed, gp.tiles_captured, gp.survived,
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


# 创建全局数据库实例
db = Database()