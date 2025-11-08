#!/usr/bin/env python3
"""创建测试用户的脚本"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flagwars.database import Database

def create_test_user():
    """创建测试用户"""
    db = Database("flagwars.db")
    
    # 创建测试用户
    username = "testuser"
    password = "testpass"
    email = "test@example.com"
    
    user_id = db.create_user(username, password, email)
    
    if user_id:
        print(f"成功创建测试用户: {username} (ID: {user_id})")
        print(f"密码: {password}")
        return True
    else:
        print(f"创建用户失败，可能用户名 '{username}' 已存在")
        return False

if __name__ == "__main__":
    create_test_user()