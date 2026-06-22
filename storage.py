"""SQLite 存储层 —— 统一数据持久化与去重 + API Key 管理"""

import sqlite3
import os
import json
import time
from datetime import datetime

# 支持环境变量配置数据目录（用于 Railway/云部署挂载持久化卷）
_DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
DB_PATH = os.path.join(_DATA_DIR, "monitor.db")


class Store:
    def __init__(self, path: str = DB_PATH, retention_days: int = 30):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.retention_days = retention_days
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=30000")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                description TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                extra TEXT DEFAULT '',
                fetched_at INTEGER NOT NULL,
                UNIQUE(source, url)
            );
            CREATE INDEX IF NOT EXISTS idx_items_source ON items(source);
            CREATE INDEX IF NOT EXISTS idx_items_fetched ON items(fetched_at);
            CREATE INDEX IF NOT EXISTS idx_items_tags ON items(tags);

            -- API Key 表
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT UNIQUE NOT NULL,
                key_prefix TEXT NOT NULL,
                tier TEXT NOT NULL,
                name TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                daily_used INTEGER DEFAULT 0,
                daily_date TEXT DEFAULT '',
                expires_at TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_apikeys_hash ON api_keys(key_hash);
        """)
        self.conn.commit()
        self._migrate_old_tables()

    def _migrate_old_tables(self):
        """移除旧版用户/订单/Session 表，重建无 user_id 的 api_keys 表"""
        old_tables = {"users", "user_sessions", "sms_codes", "orders"}
        existing = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if old_tables & existing:
            for t in old_tables:
                if t in existing:
                    self.conn.execute(f"DROP TABLE IF EXISTS {t}")
            # 重建 api_keys 表为新 schema
            self.conn.execute("DROP TABLE IF EXISTS api_keys")
            self.conn.executescript("""
                CREATE TABLE api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash TEXT UNIQUE NOT NULL,
                    key_prefix TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    name TEXT DEFAULT '',
                    is_active INTEGER DEFAULT 1,
                    daily_used INTEGER DEFAULT 0,
                    daily_date TEXT DEFAULT '',
                    expires_at TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_apikeys_hash ON api_keys(key_hash);
            """)
            self.conn.commit()
            print("[migrate] 已移除旧版用户/支付表，api_keys 已重建")

    # ── 原有 items 方法 ──

    def upsert(self, source: str, title: str, url: str,
               description: str = "", tags: list = None,
               extra: dict = None, fetched_at: float = None) -> bool:
        if fetched_at is None:
            fetched_at = time.time()
        tags_str = ",".join(tags) if tags else ""
        extra_str = json.dumps(extra, ensure_ascii=False) if extra else ""
        for attempt in range(3):
            try:
                cur = self.conn.execute(
                    """INSERT OR IGNORE INTO items
                       (source, title, url, description, tags, extra, fetched_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (source, title, url, description, tags_str, extra_str, int(fetched_at))
                )
                self.conn.commit()
                return cur.rowcount > 0
            except sqlite3.OperationalError:
                if attempt < 2:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                return False
            except Exception:
                return False

    def query(self, source: str = None, tag: str = None,
              limit: int = 100, offset: int = 0, hours: int = None) -> list:
        sql = "SELECT * FROM items WHERE 1=1"
        params = []
        if source:
            sql += " AND source = ?"
            params.append(source)
        if tag:
            sql += " AND tags LIKE ?"
            params.append(f"%{tag}%")
        if hours:
            cutoff = int(time.time()) - hours * 3600
            sql += " AND fetched_at >= ?"
            params.append(cutoff)
        sql += " ORDER BY fetched_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        return [dict(r) for r in self.conn.execute(sql, params)]

    def stats(self) -> dict:
        rows = self.conn.execute(
            "SELECT source, COUNT(*) as cnt, MAX(fetched_at) as last_fetch "
            "FROM items GROUP BY source ORDER BY cnt DESC"
        ).fetchall()
        sources = {}
        for r in rows:
            sources[r["source"]] = {
                "count": r["cnt"],
                "last_fetch": datetime.fromtimestamp(r["last_fetch"]).strftime("%m-%d %H:%M"),
            }
        total = self.conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        return {"total": total, "sources": sources}

    def cleanup_old(self):
        cutoff = int(time.time()) - self.retention_days * 86400
        deleted = self.conn.execute(
            "DELETE FROM items WHERE fetched_at < ?", (cutoff,)
        ).rowcount
        self.conn.commit()
        if deleted:
            print(f"  [清理] 删除 {deleted} 条过期数据")

    # ── API Key 方法 ──

    def create_api_key(self, key_hash: str, key_prefix: str, tier: str, name: str = "", expires_at: str = "") -> int:
        now = datetime.now().isoformat()
        cur = self.conn.execute(
            """INSERT INTO api_keys (key_hash, key_prefix, tier, name, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (key_hash, key_prefix, tier, name, expires_at or '', now)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_api_key_by_hash(self, key_hash: str) -> dict:
        row = self.conn.execute("SELECT * FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
        return dict(row) if row else None

    def revoke_api_key(self, key_id: int) -> bool:
        self.conn.execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_id,))
        self.conn.commit()
        return self.conn.total_changes > 0

    def increment_key_usage(self, key_hash: str):
        today = datetime.now().strftime("%Y-%m-%d")
        self.conn.execute(
            "UPDATE api_keys SET daily_used = daily_used + 1, daily_date = ? WHERE key_hash = ?",
            (today, key_hash)
        )
        self.conn.commit()

    def reset_key_daily_usage(self, key_id: int):
        self.conn.execute("UPDATE api_keys SET daily_used = 0, daily_date = '' WHERE id = ?", (key_id,))
        self.conn.commit()

    def list_all_api_keys(self) -> list:
        return [dict(r) for r in self.conn.execute("SELECT * FROM api_keys WHERE is_active = 1 ORDER BY created_at DESC").fetchall()]

    # ── 迁移：api_keys.json → SQLite ──

    def migrate_keys_from_json(self, json_path: str):
        if not os.path.exists(json_path):
            return
        with open(json_path, "r", encoding="utf-8") as f:
            legacy = json.load(f)
        count = 0
        for key_hash, info in legacy.items():
            existing = self.get_api_key_by_hash(key_hash)
            if not existing:
                self.conn.execute(
                    """INSERT INTO api_keys (key_hash, key_prefix, tier, name, daily_used, daily_date, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (key_hash, key_hash[:12], info.get("tier", "free"),
                     info.get("name", ""), info.get("daily_used", 0),
                     info.get("daily_date", ""), info.get("created", datetime.now().isoformat()))
                )
                count += 1
        self.conn.commit()
        if count > 0:
            # 备份旧文件
            bak = json_path + ".bak"
            if not os.path.exists(bak):
                os.rename(json_path, bak)
            print(f"[migrate] 从 api_keys.json 迁移了 {count} 个 Key → SQLite")

    def close(self):
        self.conn.close()
