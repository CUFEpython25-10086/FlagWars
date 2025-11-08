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
                    losses INTEGER DEFAULT 0
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
            
            # 用户解锁背景音乐表
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
            
            # 用户解锁胜利音乐表
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
            
            # 用户选择的背景音乐表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_selected_bgm (
                    user_id INTEGER PRIMARY KEY,
                    bgm_name TEXT NOT NULL DEFAULT 'Whispers-of-Strategy.mp3',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 用户选择的胜利音乐表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_selected_victory_music (
                    user_id INTEGER PRIMARY KEY,
                    victory_music_name TEXT NOT NULL DEFAULT 'royal-vict.mp3',
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
                user_id = cursor.lastrowid
                
                # 为用户设置默认音乐选择
                cursor.execute(
                    "INSERT INTO user_selected_bgm (user_id, bgm_name) VALUES (?, ?)",
                    (user_id, 'Whispers-of-Strategy.mp3')
                )
                cursor.execute(
                    "INSERT INTO user_selected_victory_music (user_id, victory_music_name) VALUES (?, ?)",
                    (user_id, 'royal-vict.mp3')
                )
                
                # 为用户解锁默认音乐
                cursor.execute(
                    "INSERT INTO user_unlocked_bgm (user_id, music_name) VALUES (?, ?)",
                    (user_id, 'Whispers-of-Strategy.mp3')
                )
                cursor.execute(
                    "INSERT INTO user_unlocked_victory_music (user_id, music_name) VALUES (?, ?)",
                    (user_id, 'royal-vict.mp3')
                )
                
                conn.commit()
                return user_id
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
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """获取用户统计信息"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT 
                    total_games, wins, losses
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
                
                # 计算胜率
                win_rate = 0
                if total_games > 0:
                    win_rate = round(wins * 100.0 / total_games, 2)
                
                return {
                    'total_games': total_games,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate
                }
            
            # 如果用户不存在，返回默认值
            return {
                'total_games': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0
            }
    
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
    
    def record_game_player(self, game_id: int, user_id: int, final_rank: int, survived: bool):
        """记录游戏参与者信息"""
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
    
    def get_available_music(self):
        """获取所有可用的音乐"""
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
            return {
                'bgm': ['Whispers-of-Strategy.mp3'],
                'victory': ['royal-vict.mp3']
            }
    
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
    
    def get_user_music_settings(self, user_id):
        """获取用户音乐设置"""
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
            return {
                'selected_bgm': 'Whispers-of-Strategy.mp3',
                'selected_victory': 'royal-vict.mp3',
                'unlocked_bgm': ['Whispers-of-Strategy.mp3'],
                'unlocked_victory': ['royal-vict.mp3']
            }
    
    def update_user_music_selection(self, user_id, bgm_name=None, victory_music_name=None):
        """更新用户音乐选择"""
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
        """解锁背景音乐"""
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
        """解锁胜利音乐"""
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
        """获取用户已解锁的背景音乐列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT music_name FROM user_unlocked_bgm WHERE user_id = ?",
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]
    
    def get_unlocked_victory_music(self, user_id: int) -> List[str]:
        """获取用户已解锁的胜利音乐列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT music_name FROM user_unlocked_victory_music WHERE user_id = ?",
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]
    
    def is_bgm_unlocked(self, user_id: int, music_name: str) -> bool:
        """检查背景音乐是否已解锁"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM user_unlocked_bgm WHERE user_id = ? AND music_name = ?",
                (user_id, music_name)
            )
            return cursor.fetchone() is not None
    
    def is_victory_music_unlocked(self, user_id: int, music_name: str) -> bool:
        """检查胜利音乐是否已解锁"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM user_unlocked_victory_music WHERE user_id = ? AND music_name = ?",
                (user_id, music_name)
            )
            return cursor.fetchone() is not None


# 创建全局数据库实例
db = Database()