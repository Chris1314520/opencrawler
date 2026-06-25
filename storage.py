"""SQLite 存储层 —— 统一数据持久化与去重 + API Key 管理"""

import sqlite3
import os
import json
import time
import threading
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
        # 线程安全写锁：保护所有写操作（读操作不加锁，WAL 模式支持并发读）
        self._write_lock = threading.Lock()
        # stats() 的 TTL 缓存（60 秒），避免频繁全表扫描
        self._stats_cache = None
        self._stats_cache_ts = 0.0
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
            CREATE INDEX IF NOT EXISTS idx_items_source_fetched ON items(source, fetched_at DESC);

            -- API Key 表（key_hash 已有 UNIQUE 约束，自动建索引，无需再建 idx_apikeys_hash）
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
        """)
        # 清理冗余/无效索引：
        #   idx_items_tags —— tags 以逗号分隔存储，LIKE 查询无法利用该索引
        #   idx_apikeys_hash —— key_hash 已有 UNIQUE 约束自动建索引，重复
        self.conn.executescript("""
            DROP INDEX IF EXISTS idx_items_tags;
            DROP INDEX IF EXISTS idx_apikeys_hash;
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
                with self._write_lock:
                    cur = self.conn.execute(
                        """INSERT OR REPLACE INTO items
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

    def upsert_many(self, source: str, items: list[dict]) -> int:
        """批量 upsert：用 executemany + 单次 commit 处理一批记录。

        items: list[dict]，每个 dict 含 title, url, description, tags, extra 字段。
        tags 可为 list（按逗号拼接）或已拼接的字符串；extra 为 dict（JSON 序列化）。
        返回新增/更新的数量。
        """
        if not items:
            return 0
        now = int(time.time())
        rows = []
        for it in items:
            tags = it.get("tags")
            if isinstance(tags, (list, tuple)):
                tags_str = ",".join(tags)
            else:
                tags_str = tags or ""
            extra = it.get("extra")
            extra_str = json.dumps(extra, ensure_ascii=False) if extra else ""
            fetched_at = int(it.get("fetched_at") or now)
            rows.append((
                source,
                it.get("title", ""),
                it.get("url", ""),
                it.get("description", "") or "",
                tags_str,
                extra_str,
                fetched_at,
            ))
        with self._write_lock:
            try:
                self.conn.executemany(
                    """INSERT OR REPLACE INTO items
                       (source, title, url, description, tags, extra, fetched_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    rows,
                )
                self.conn.commit()
                return len(rows)
            except Exception as e:
                self.conn.rollback()
                print(f"[upsert_many] 批量写入失败: {e}")
                return 0

    @staticmethod
    def _tag_match(tag: str):
        """生成按逗号边界匹配单个 tag 的 SQL 片段与参数列表。

        tags 字段以逗号分隔存储（如 "RSS,HN,AI"）。用逗号边界匹配可避免
        子串误匹配（查询 "A" 不会命中 "AI"）。覆盖四种位置：
        唯一(tags=?) / 首位(tags LIKE 'tag,%') / 末位(tags LIKE '%,tag') / 中间(tags LIKE '%,tag,%')。
        """
        return ("(tags = ? OR tags LIKE ? OR tags LIKE ? OR tags LIKE ?)",
                [tag, f"{tag},%", f"%,{tag}", f"%,{tag},%"])

    def query(self, source: str = None, tag: str = None,
              limit: int = 100, offset: int = 0, hours: int = None) -> list:
        sql = "SELECT * FROM items WHERE 1=1"
        params = []
        if source:
            sql += " AND source = ?"
            params.append(source)
        if tag:
            # tags 以逗号分隔存储（如 "RSS,HN,AI"），用逗号边界匹配避免子串误匹配
            clause, tparams = self._tag_match(tag)
            sql += " AND " + clause
            params.extend(tparams)
        if hours:
            cutoff = int(time.time()) - hours * 3600
            sql += " AND fetched_at >= ?"
            params.append(cutoff)
        sql += " ORDER BY fetched_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        return [dict(r) for r in self.conn.execute(sql, params)]

    def count(self, source: str = None, tag: str = None, hours: int = None) -> int:
        """用 SQL SELECT COUNT(*) 计数，替代 Python 内存计数。支持按 source/tag/hours 过滤。"""
        sql = "SELECT COUNT(*) FROM items WHERE 1=1"
        params = []
        if source:
            sql += " AND source = ?"
            params.append(source)
        if tag:
            clause, tparams = self._tag_match(tag)
            sql += " AND " + clause
            params.extend(tparams)
        if hours:
            cutoff = int(time.time()) - hours * 3600
            sql += " AND fetched_at >= ?"
            params.append(cutoff)
        return self.conn.execute(sql, params).fetchone()[0]

    def stats(self) -> dict:
        # TTL 缓存（60 秒），避免频繁全表扫描
        now = time.time()
        if self._stats_cache is not None and (now - self._stats_cache_ts) < 60:
            return self._stats_cache
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
        result = {"total": total, "sources": sources}
        self._stats_cache = result
        self._stats_cache_ts = now
        return result

    def cleanup_old(self):
        cutoff = int(time.time()) - self.retention_days * 86400
        with self._write_lock:
            deleted = self.conn.execute(
                "DELETE FROM items WHERE fetched_at < ?", (cutoff,)
            ).rowcount
            self.conn.commit()
        if deleted:
            print(f"  [清理] 删除 {deleted} 条过期数据")

    # ── API Key 方法 ──

    def create_api_key(self, key_hash: str, key_prefix: str, tier: str, name: str = "", expires_at: str = "") -> int:
        now = datetime.now().isoformat()
        with self._write_lock:
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
        with self._write_lock:
            self.conn.execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_id,))
            self.conn.commit()
            return self.conn.total_changes > 0

    def increment_key_usage(self, key_hash: str):
        today = datetime.now().strftime("%Y-%m-%d")
        with self._write_lock:
            self.conn.execute(
                "UPDATE api_keys SET daily_used = daily_used + 1, daily_date = ? WHERE key_hash = ?",
                (today, key_hash)
            )
            self.conn.commit()

    def reset_key_daily_usage(self, key_id: int):
        with self._write_lock:
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
