# db.py
import sqlite3
from datetime import datetime
import asyncio
import os
from pathlib import Path
from decimal import Decimal


class Lighter_Dao:
    # def __init__(self, db_path: str = "/home/admin/myproject/data/monitor.db"):
    def __init__(self, db_path: str = "../data/monitor.db"):

        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_tables()

    # ========================================
    # 内部：判断表是否存在
    # ========================================
    def _table_exists(self, conn, table_name: str) -> bool:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return cur.fetchone() is not None

    # ========================================
    # 构造时：判断 + 创建所有表
    # ========================================
    def _init_tables(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # 1. account_snapshots
        if not self._table_exists(conn, "account_snapshots"):
            cur.execute('''
            CREATE TABLE account_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                balance TEXT NOT NULL,
                pnl REAL DEFAULT 0,
                UNIQUE(account_id, timestamp)
            )
            ''')
            print("[DB] Created table: account_snapshots")

        # 2. position_records
        if not self._table_exists(conn, "position_records"):
            cur.execute('''
            CREATE TABLE position_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                account_index INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                quantity REAL NOT NULL,
                amount REAL NOT NULL,
                direction TEXT NOT NULL,        
                entry_price REAL NOT NULL,      
                create_time TEXT NOT NULL
            )
            ''')
            print("[DB] Created table: position_records")

        conn.commit()
        conn.close()

    # ========================================
    # 1. 获取初始余额
    # ========================================
    def get_initial_balance(self, account_index: int) -> Decimal:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute('''
        SELECT balance FROM account_snapshots 
        WHERE account_id = ? 
        ORDER BY timestamp ASC LIMIT 1
        ''', (str(account_index),))
        row = cur.fetchone()
        conn.close()
        return Decimal(row[0]) if row else Decimal('0')

    # ========================================
    # 2. 保存快照 + 返回 PNL
    # ========================================
    def save_snapshot(self, account_id: str, balance: Decimal) -> float:
        initial = self.get_initial_balance(int(account_id))
        pnl = float(balance - initial)
        timestamp = datetime.utcnow().isoformat()

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute('''
            INSERT INTO account_snapshots (account_id, timestamp, balance, pnl)
            VALUES (?, ?, ?, ?)
            ''', (account_id, timestamp, str(balance), pnl))
            conn.commit()
            print(f"[DB SUCCESS] Saved snapshot: {account_id} | balance: {balance} | pnl: {pnl:+.2f}")
        except sqlite3.IntegrityError:
            pass  # 已存在
        except Exception as e:
            print(f"[DB ERROR] Save snapshot failed: {account_id} | Error: {e}")
        finally:
            conn.close()
        return pnl

    # ========================================
    # 3. 获取最新账户状态
    # ========================================
    def get_latest_accounts(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute('''
            SELECT account_id, balance, pnl 
            FROM account_snapshots 
            WHERE id IN (
                SELECT MAX(id) FROM account_snapshots GROUP BY account_id
            )
            ''')
            rows = cur.fetchall()
            result = [{"account_id": r[0], "balance": r[1], "pnl": r[2]} for r in rows]
            print(f"[DB] Fetched latest accounts: {len(result)} records")
            return result
        except Exception as e:
            print(f"[DB ERROR] get_latest_accounts failed: {e}")
            return []
        finally:
            conn.close()

    # ========================================
    # 4. 异步写入 position（不阻塞 + 打印日志）
    # ========================================
    def _save_position_sync(self, account_id: str, account_index: int, ticker: str, 
                           quantity: float, amount: float, direction: str, entry_price: float, create_time: str):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('''
            INSERT INTO position_records 
            (account_id, account_index, ticker, quantity, amount, direction, entry_price, create_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (account_id, account_index, ticker, quantity, amount, direction, entry_price, create_time))
            conn.commit()
            conn.close()
            print(f"[DB SUCCESS] Saved position: {ticker} | {quantity:.6f} | {direction} | price: {entry_price:.2f}")
        except Exception as e:
            print(f"[DB ERROR] Failed to save position: {ticker} | {account_id} | Error: {e}")

    async def save_position_record(self, account_id: str, account_index: int, ticker: str, 
                                  quantity: float, amount: float, direction: str, entry_price: float):
        create_time = datetime.utcnow().isoformat()
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                self._save_position_sync, 
                account_id, account_index, ticker, quantity, amount, direction, entry_price, create_time
            )
        except Exception as e:
            print(f"[DB ASYNC ERROR] Task failed for {ticker} | {account_id} | Error: {e}")

    # ========================================
    # 5. 统计 amount 总和
    # ========================================
    # db.py 在 Lighter_Dao 类中新增方法
    def get_position_amount_sum_by_account(self, account_index: int, start_time: str = None, end_time: str = None) -> float:
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            if start_time and end_time:
                # 按时间范围 + 账户
                cur.execute('''
                SELECT COALESCE(SUM(amount), 0) FROM position_records 
                WHERE account_index = ? AND create_time BETWEEN ? AND ?
                ''', (account_index, start_time, end_time))
                print(f"[DB] Amount sum for account {account_index}: {start_time} to {end_time}")
            else:
                # 按账户查询所有记录
                cur.execute('''
                SELECT COALESCE(SUM(amount), 0) FROM position_records 
                WHERE account_index = ?
                ''', (account_index,))
                print(f"[DB] Amount sum for account {account_index}: ALL RECORDS")

            result = cur.fetchone()[0]
            conn.close()
            total = float(result)
            print(f"[DB] Account {account_index} total volume: ${total:,.2f}")
            return total

        except Exception as e:
            print(f"[DB ERROR] get_position_amount_sum_by_account {account_index} failed: {e}")
            return 0.0