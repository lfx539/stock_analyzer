# SQLite数据库管理

import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "stocks.db"

def get_db_connection():
    """获取数据库连接"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """初始化数据库表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 自选股表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL UNIQUE,
            stock_name TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {DB_PATH}")

# 数据库操作类
class Database:
    @staticmethod
    def add_watchlist(stock_code: str, stock_name: str = None, notes: str = None) -> bool:
        """添加自选股"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO watchlist (stock_code, stock_name, notes) VALUES (?, ?, ?)",
                (stock_code, stock_name, notes)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def remove_watchlist(stock_code: str) -> bool:
        """删除自选股"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM watchlist WHERE stock_code = ?", (stock_code,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def get_watchlist() -> List[Dict]:
        """获取自选股列表"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM watchlist ORDER BY added_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def is_in_watchlist(stock_code: str) -> bool:
        """检查股票是否在自选股中"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM watchlist WHERE stock_code = ?", (stock_code,))
            return cursor.fetchone() is not None
        finally:
            conn.close()

# 初始化数据库
init_database()
