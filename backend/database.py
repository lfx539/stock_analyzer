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

    # PE/PB历史数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pe_pb_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            pe_ttm REAL,
            pb REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stock_code, trade_date)
        )
    ''')

    # 价格预警表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL,
            stock_name TEXT,
            target_price REAL NOT NULL,
            alert_type TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            triggered_at TIMESTAMP
        )
    ''')

    # 投资组合表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            initial_capital REAL NOT NULL,
            cash REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 交易记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_id INTEGER NOT NULL,
            stock_code TEXT NOT NULL,
            stock_name TEXT,
            trans_type TEXT NOT NULL,
            shares REAL NOT NULL,
            price REAL NOT NULL,
            amount REAL NOT NULL,
            trans_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
        )
    ''')

    # 创建索引加速查询
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pe_pb_stock_date
        ON pe_pb_history(stock_code, trade_date)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_alerts_status
        ON price_alerts(status)
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

    @staticmethod
    def save_pe_pb_history(stock_code: str, trade_date: str, pe_ttm: float = None, pb: float = None):
        """保存PE/PB历史数据"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO pe_pb_history (stock_code, trade_date, pe_ttm, pb)
                VALUES (?, ?, ?, ?)
            ''', (stock_code, trade_date, pe_ttm, pb))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_pe_pb_history(stock_code: str, limit: int = 250) -> List[Dict]:
        """获取PE/PB历史数据"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT stock_code, trade_date, pe_ttm, pb
                FROM pe_pb_history
                WHERE stock_code = ?
                ORDER BY trade_date DESC
                LIMIT ?
            ''', (stock_code, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def get_pe_pb_history_count(stock_code: str) -> int:
        """获取历史数据条数"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT COUNT(*) FROM pe_pb_history WHERE stock_code = ?
            ''', (stock_code,))
            result = cursor.fetchone()
            return result[0] if result else 0
        finally:
            conn.close()

    # ========== 价格预警相关 ==========
    @staticmethod
    def add_alert(stock_code: str, stock_name: str, target_price: float, alert_type: str) -> int:
        """添加价格预警"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO price_alerts (stock_code, stock_name, target_price, alert_type)
                VALUES (?, ?, ?, ?)
            ''', (stock_code, stock_name, target_price, alert_type))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def remove_alert(alert_id: int) -> bool:
        """删除价格预警"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM price_alerts WHERE id = ?", (alert_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def get_alerts(status: str = None) -> List[Dict]:
        """获取预警列表"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if status:
                cursor.execute(
                    "SELECT * FROM price_alerts WHERE status = ? ORDER BY created_at DESC",
                    (status,)
                )
            else:
                cursor.execute("SELECT * FROM price_alerts ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def get_active_alerts() -> List[Dict]:
        """获取所有活跃预警"""
        return Database.get_alerts(status='active')

    @staticmethod
    def trigger_alert(alert_id: int) -> bool:
        """标记预警为已触发"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE price_alerts
                SET status = 'triggered', triggered_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (alert_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    # ========== 投资组合相关 ==========
    @staticmethod
    def create_portfolio(name: str, initial_capital: float) -> int:
        """创建投资组合"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO portfolios (name, initial_capital, cash)
                VALUES (?, ?, ?)
            ''', (name, initial_capital, initial_capital))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def get_portfolios() -> List[Dict]:
        """获取所有投资组合"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM portfolios ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def get_portfolio(portfolio_id: int) -> Optional[Dict]:
        """获取单个投资组合"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def update_portfolio_cash(portfolio_id: int, cash: float) -> bool:
        """更新组合现金"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE portfolios SET cash = ? WHERE id = ?", (cash, portfolio_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def delete_portfolio(portfolio_id: int) -> bool:
        """删除投资组合及其交易记录"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 先删除交易记录
            cursor.execute("DELETE FROM transactions WHERE portfolio_id = ?", (portfolio_id,))
            # 再删除组合
            cursor.execute("DELETE FROM portfolios WHERE id = ?", (portfolio_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def rename_portfolio(portfolio_id: int, new_name: str) -> bool:
        """重命名投资组合"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE portfolios SET name = ? WHERE id = ?", (new_name, portfolio_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def add_transaction(portfolio_id: int, stock_code: str, stock_name: str,
                        trans_type: str, shares: float, price: float, amount: float) -> int:
        """添加交易记录"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO transactions (portfolio_id, stock_code, stock_name, trans_type, shares, price, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (portfolio_id, stock_code, stock_name, trans_type, shares, price, amount))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def get_transactions(portfolio_id: int) -> List[Dict]:
        """获取交易记录"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM transactions WHERE portfolio_id = ? ORDER BY trans_date DESC",
                (portfolio_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def get_holdings(portfolio_id: int) -> List[Dict]:
        """获取当前持仓"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT stock_code, stock_name,
                       SUM(CASE WHEN trans_type = 'buy' THEN shares ELSE -shares END) as shares,
                       SUM(CASE WHEN trans_type = 'buy' THEN amount ELSE -amount END) as cost
                FROM transactions
                WHERE portfolio_id = ?
                GROUP BY stock_code
                HAVING shares > 0
            ''', (portfolio_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

# 初始化数据库
init_database()
