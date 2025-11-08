"""账号系统相关API"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from tornado import web

from .database import db


class BaseHandler(web.RequestHandler):
    """基础请求处理器，提供通用功能"""
    
    def prepare(self):
        """请求前的准备工作"""
        # 设置CORS头
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, X-Requested-With")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    
    def options(self):
        """处理OPTIONS请求"""
        self.set_status(204)
        self.finish()
    
    def get_current_user(self):
        """获取当前登录用户"""
        session_token = self.get_cookie("session_token")
        if not session_token:
            return None
        
        user = db.verify_session(session_token)
        return user
    
    def write_json(self, data):
        """写入JSON响应"""
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(data))


class LoginHandler(BaseHandler):
    """用户登录处理器"""
    
    async def post(self):
        """处理登录请求"""
        try:
            data = json.loads(self.request.body.decode())
            username = data.get('username', '').strip()
            password = data.get('password', '')
            
            if not username or not password:
                self.write_json({
                    'success': False,
                    'message': '用户名和密码不能为空'
                })
                return
            
            # 验证用户
            user = db.verify_user(username, password)
            if not user:
                self.set_status(401)  # 未授权状态码
                self.write_json({
                    'success': False,
                    'message': '用户名或密码错误'
                })
                return
            
            # 获取用户统计信息
            stats = db.get_user_stats(user['id'])
            
            # 创建会话
            session_token = db.create_session(user['id'])
            
            # 设置会话Cookie
            self.set_cookie(
                "session_token", 
                session_token,
                expires_days=1,
                httponly=True
            )
            
            self.write_json({
                'success': True,
                'message': '登录成功',
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'stats': stats or {}
                }
            })
            
        except Exception as e:
            logging.error(f"登录错误: {str(e)}")
            self.write_json({
                'success': False,
                'message': '登录失败，请稍后再试'
            })


class RegisterHandler(BaseHandler):
    """用户注册处理器"""
    
    async def post(self):
        """处理注册请求"""
        try:
            data = json.loads(self.request.body.decode())
            username = data.get('username', '').strip()
            password = data.get('password', '')
            email = data.get('email', '').strip() or None
            
            if not username or not password:
                self.write_json({
                    'success': False,
                    'message': '用户名和密码不能为空'
                })
                return
            
            if len(username) < 3 or len(username) > 20:
                self.write_json({
                    'success': False,
                    'message': '用户名长度必须在3-20个字符之间'
                })
                return
            
            if len(password) < 6:
                self.write_json({
                    'success': False,
                    'message': '密码长度不能少于6个字符'
                })
                return
            
            # 创建用户
            user_id = db.create_user(username, password, email)
            if not user_id:
                self.write_json({
                    'success': False,
                    'message': '用户名或邮箱已存在'
                })
                return
            
            self.write_json({
                'success': True,
                'message': '注册成功，请登录'
            })
            
        except Exception as e:
            logging.error(f"注册错误: {str(e)}")
            self.write_json({
                'success': False,
                'message': '注册失败，请稍后再试'
            })


class LogoutHandler(BaseHandler):
    """用户登出处理器"""
    
    async def post(self):
        """处理登出请求"""
        try:
            session_token = self.get_cookie("session_token")
            if session_token:
                db.invalidate_session(session_token)
            
            # 清除Cookie
            self.clear_cookie("session_token")
            
            self.write_json({
                'success': True,
                'message': '已成功登出'
            })
            
        except Exception as e:
            logging.error(f"登出错误: {str(e)}")
            self.write_json({
                'success': False,
                'message': '登出失败，请稍后再试'
            })


class CheckAuthHandler(BaseHandler):
    """检查用户认证状态处理器"""
    
    async def get(self):
        """检查当前用户是否已登录"""
        try:
            user = self.get_current_user()
            if user:
                # 获取用户统计信息
                stats = db.get_user_stats(user['id'])
                
                self.write_json({
                    'authenticated': True,
                    'user': {
                        'id': user['id'],
                        'username': user['username'],
                        'email': user['email'],
                        'stats': stats or {}
                    }
                })
            else:
                self.write_json({
                    'authenticated': False
                })
                
        except Exception as e:
            logging.error(f"检查认证状态错误: {str(e)}")
            self.write_json({
                'authenticated': False,
                'error': '检查认证状态失败'
            })


class UserStatsHandler(BaseHandler):
    """用户统计信息处理器"""
    
    async def get(self):
        """获取用户统计信息"""
        try:
            user = self.get_current_user()
            if not user:
                self.write_json({
                    'success': False,
                    'message': '请先登录'
                })
                return
            
            # 获取用户统计信息
            stats = db.get_user_stats(user['id'])
            
            self.write_json({
                'success': True,
                'stats': stats or {}
            })
            
        except Exception as e:
            logging.error(f"获取用户统计信息错误: {str(e)}")
            self.write_json({
                'success': False,
                'message': '获取统计信息失败，请稍后再试'
            })


class GameHistoryHandler(BaseHandler):
    """游戏历史记录处理器"""
    
    async def get(self):
        """获取用户游戏历史"""
        try:
            user = self.get_current_user()
            if not user:
                self.write_json({
                    'success': False,
                    'message': '请先登录'
                })
                return
            
            # 获取分页参数
            limit = int(self.get_argument('limit', 10))
            limit = min(max(limit, 1), 50)  # 限制在1-50之间
            
            # 获取游戏历史
            history = db.get_user_game_history(user['id'], limit)
            
            self.write_json({
                'success': True,
                'history': history
            })
            
        except Exception as e:
            logging.error(f"获取游戏历史错误: {str(e)}")
            self.write_json({
                'success': False,
                'message': '获取游戏历史失败，请稍后再试'
            })


# 路由配置
auth_routes = [
    (r"/api/auth/login", LoginHandler),
    (r"/api/auth/register", RegisterHandler),
    (r"/api/auth/logout", LogoutHandler),
    (r"/api/auth/me", CheckAuthHandler),  # 修改为/me，与前端匹配
    (r"/api/user/stats", UserStatsHandler),
    (r"/api/user/history", GameHistoryHandler),
]