#!/usr/bin/env python3
"""统一事件监视器 —— Web 面板 + 定时抓取，一个入口"""

import argparse
import hashlib
import json
import os
import re
import secrets
import requests
import sys
import time
from functools import wraps

import yaml
from datetime import datetime
from threading import Thread

from flask import Flask, render_template, request, jsonify, g, session, redirect, send_file
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

sys.path.insert(0, os.path.dirname(__file__))
from storage import Store
from notifier import Notifier
from fetchers.github_trending import GitHubTrendingFetcher
from fetchers.hackernews import HackerNewsFetcher
from fetchers.rss_feeds import RSSFetcherWithProxy
from fetchers.curl_cffi_rss import CurlCffiRSSFetcher
from fetchers.nvd_cve import NVDCVEFetcher
from fetchers.shortvideo_trending import ShortVideoTrendingFetcher
from fetchers.finance_data import FinanceDataFetcher

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

# ── 来源中文名映射 ──
SOURCE_LABELS = {
    "github_trending": "GitHub 趋势榜",
    "hackernews": "Hacker News",
    "rss": "RSS 订阅",
    "curl_cffi_rss": "RSS (反爬)",
    "nvd_cve": "CVE 漏洞",
    "shortvideo_trending": "短视频热门",
    "finance_data": "金融数据",
}

# 来源分类（用于前端分组展示）
SOURCE_CATEGORIES = {
    "github_trending": "代码",
    "hackernews": "海外",
    "rss": "资讯",
    "curl_cffi_rss": "资讯",
    "nvd_cve": "安全",
    "shortvideo_trending": "短视频",
    "finance_data": "金融",
}

TAG_LABELS = {
    "GitHub": "GitHub",
    "trending": "热门",
    "HackerNews": "HN",
    "RSS": "RSS",
    "AI": "AI",
    "安全": "安全",
    "CVE": "CVE",
    "严重": "严重",
    "高危": "高危",
    "技术": "技术",
    "中文": "中文",
    "编程": "编程",
    "英文": "英文",
    "论文": "论文",
    "金融": "金融",
    "科技": "科技",
    "代码": "代码",
}


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Flask App ──
app = Flask(__name__)
store = Store()
config = load_config()
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or config.get("secret_key") or secrets.token_urlsafe(32)
app.jinja_env.auto_reload = True

# No blueprints — single-user mode

# ── Admin Key (for dashboard & management endpoints) ──
ADMIN_KEY = os.environ.get("ADMIN_KEY") or config.get("admin_key", "") or f"admin_{secrets.token_urlsafe(32)}"
if not os.environ.get("ADMIN_KEY") and not config.get("admin_key", ""):
    print(f"[admin] Auto-generated Admin Key: {ADMIN_KEY}")
    print(f"[admin] Set ADMIN_KEY env var or add admin_key to config.yaml to persist.")

# ── API Routes ──
# ── API Key 鉴权模块 ──
# 参考: Stripe API Key 模式 + gpt4free 哈希存储 + flask_limiter 限流

API_KEYS_FILE = os.path.join(BASE_DIR, "api_keys.json")
KEY_PREFIX = "sk-"

TIER_LIMITS = {
    "free":     {"daily": 20,   "rpm": 5},
    "pro":      {"daily": 500,  "rpm": 30},
    "team":     {"daily": 9999, "rpm": 60},
}


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _load_keys() -> dict:
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_keys(keys: dict):
    with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)


# API_KEYS migrated to SQLite (api_keys table)
# Legacy api_keys.json will be auto-migrated on startup


# old create_api_key migrated to storage.py


# old revoke_api_key migrated to storage.py


def require_api_key(f):
    """装饰器：从 X-API-Key header 提取并验证 Key，查询 SQLite，注入 g.api_tier 和 g.api_info"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-Key", "") or request.args.get("api_key", "")
        if not key:
            return jsonify({"error": "missing api key", "hint": "Pass X-API-Key header or ?api_key= query param"}), 401

        h = _hash(key)
        info = store.get_api_key_by_hash(h)
        if info is None or not info.get("is_active"):
            return jsonify({"error": "invalid api key"}), 401

        # 过期检查
        if info.get("expires_at"):
            from datetime import datetime as _dt
            try:
                if _dt.fromisoformat(info["expires_at"]) < _dt.now():
                    return jsonify({"error": "api key expired"}), 401
            except (ValueError, TypeError):
                pass

        # 日配额检查
        today = datetime.now().strftime("%Y-%m-%d")
        if info.get("daily_date") != today:
            store.reset_key_daily_usage(info["id"])
            info["daily_used"] = 0

        daily_limit = TIER_LIMITS.get(info["tier"], TIER_LIMITS["free"])["daily"]
        if info.get("daily_used", 0) >= daily_limit:
            return jsonify({
                "error": "daily quota exceeded",
                "limit": daily_limit,
                "tier": info["tier"],
                "reset_at": f"{today}T23:59:59",
            }), 429

        store.increment_key_usage(h)

        g.api_tier = info["tier"]
        g.api_info = info
        g.api_key_name = info.get("name", "")
        return f(*args, **kwargs)
    return wrapper


def require_admin(f):
    """装饰器：验证 Admin Key，保护管理端点和仪表盘 API"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        key = request.headers.get('X-Admin-Key', '') or request.args.get('admin_key', '')
        if not key or not secrets.compare_digest(key, ADMIN_KEY):
            return jsonify({"error": "unauthorized", "hint": "Pass X-Admin-Key header or ?admin_key= query param"}), 401
        return f(*args, **kwargs)
    return wrapper


def _get_or_create_demo_key():
    """Get or create a persistent demo key for the public demo page (SQLite version)"""
    demo_file = os.path.join(BASE_DIR, '.demo_key')
    if os.path.exists(demo_file):
        with open(demo_file, 'r') as f:
            raw = f.read().strip()
        if store.get_api_key_by_hash(_hash(raw)):
            return raw
    raw = f"{KEY_PREFIX}team_{secrets.token_urlsafe(32)}"
    store.create_api_key(_hash(raw), raw[:15] + "...", "team", "demo_user")
    with open(demo_file, 'w') as f:
        f.write(raw)
    return raw


# ── 对外付费 API ──

@app.route("/api/v1/trending")
@require_api_key
def api_v1_trending():
    """付费 API: 获取聚合情报数据"""
    source = request.args.get("source", "")
    keyword = request.args.get("keyword", "")
    limit = min(int(request.args.get("limit", 10)), 50)
    hours = request.args.get("hours", type=int)

    # Pro 以下用户不能查实时数据（hours=1 表示只要最新的）
    if g.api_tier == "free":
        hours = hours or 24  # Free 用户至少 6 小时延迟

    rows = store.query(source=source or None, hours=hours, limit=limit)
    if keyword:
        kw = keyword.lower()
        rows = [r for r in rows if kw in r.get("title","").lower() or kw in r.get("description","").lower()]

    for r in rows:
        r["source_label"] = SOURCE_LABELS.get(r.get("source",""), r.get("source",""))
        if isinstance(r.get("extra"), str):
            try:
                r["extra"] = json.loads(r["extra"])
            except json.JSONDecodeError:
                r["extra"] = {}

    info = g.api_info
    return jsonify({
        "items": rows,
        "total": len(rows),
        "quota": {
            "used_today": info["daily_used"],
            "daily_limit": TIER_LIMITS[g.api_tier]["daily"],
        },
        "tier": g.api_tier,
    })


@app.route("/api/v1/search")
@require_api_key
def api_v1_search():
    """付费 API: 关键词搜索"""
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "missing q parameter"}), 400
    limit = min(int(request.args.get("limit", 20)), 50)

    rows = store.query(limit=500)  # 取最近500条
    kw = q.lower()
    rows = [r for r in rows if kw in r.get("title","").lower() or kw in r.get("description","").lower()]
    rows = rows[:limit]

    for r in rows:
        r["source_label"] = SOURCE_LABELS.get(r.get("source",""), r.get("source",""))

    info = g.api_info
    return jsonify({
        "items": rows,
        "total": len(rows),
        "query": q,
        "quota": {
            "used_today": info["daily_used"],
            "daily_limit": TIER_LIMITS[g.api_tier]["daily"],
        },
    })


@app.route("/api/v1/fetch-article")
@require_api_key
def api_fetch_article():
    """抓取原文内容，返回清洗后的文本"""
    url = request.args.get("url", "")
    if not url or not url.startswith(("http://", "https://")):
        return jsonify({"error": "invalid url"}), 400

    # 禁止访问内网地址
    from urllib.parse import urlparse
    import ipaddress, socket
    host = urlparse(url).hostname or ""
    if not host:
        return jsonify({"error": "invalid url"}), 400
    try:
        addr = socket.getaddrinfo(host, None)[0][4][0]
        ip = ipaddress.ip_address(addr)
        for r in [ipaddress.ip_network("127.0.0.0/8"), ipaddress.ip_network("10.0.0.0/8"),
                   ipaddress.ip_network("172.16.0.0/12"), ipaddress.ip_network("192.168.0.0/16"),
                   ipaddress.ip_network("169.254.0.0/16"), ipaddress.ip_network("0.0.0.0/8")]:
            if ip in r:
                return jsonify({"error": "internal addresses not allowed"}), 403
    except (socket.gaierror, ValueError):
        return jsonify({"error": "cannot resolve host"}), 400

    try:
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*",
        })
        resp.encoding = resp.apparent_encoding or "utf-8"
    except Exception as e:
        return jsonify({"error": f"fetch failed: {e}"}), 502

    if resp.status_code != 200:
        return jsonify({"error": f"upstream returned {resp.status_code}"}), 502

    # 提取正文
    soup = BeautifulSoup(resp.text, "html.parser")
    # 去除无用元素
    for tag in soup.select("script, style, nav, footer, header, .sidebar, .ad, .advertisement, .comment, .comments"):
        tag.decompose()

    # 尝试找正文容器
    article = soup.select_one("article") or soup.select_one(".article") or soup.select_one(".content") or soup.select_one("main") or soup.body
    if article:
        text = article.get_text("\n", strip=True)
    else:
        text = soup.get_text("\n", strip=True)

    # 清洗：合并空行
    import re
    text = re.sub(r'\n{3,}', '\n\n', text)
    title = soup.title.string if soup.title else ""

    return jsonify({
        "title": title.strip() if title else "",
        "url": url,
        "content": text[:50000],  # 最多 50000 字
        "length": len(text),
    })


@app.route("/api/v1/download-article")
@require_api_key
def api_download_article():
    """下载原文为 TXT 文件"""
    url = request.args.get("url", "")
    fmt = request.args.get("format", "txt")  # txt 或 md
    if not url or not url.startswith(("http://", "https://")):
        return jsonify({"error": "invalid url"}), 400

    from urllib.parse import urlparse
    import ipaddress, socket
    host = urlparse(url).hostname or ""
    if not host:
        return jsonify({"error": "invalid url"}), 400
    try:
        addr = socket.getaddrinfo(host, None)[0][4][0]
        ip = ipaddress.ip_address(addr)
        for r in [ipaddress.ip_network("127.0.0.0/8"), ipaddress.ip_network("10.0.0.0/8"),
                   ipaddress.ip_network("172.16.0.0/12"), ipaddress.ip_network("192.168.0.0/16"),
                   ipaddress.ip_network("169.254.0.0/16"), ipaddress.ip_network("0.0.0.0/8")]:
            if ip in r:
                return jsonify({"error": "internal addresses not allowed"}), 403
    except (socket.gaierror, ValueError):
        return jsonify({"error": "cannot resolve host"}), 400

    try:
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*",
        })
        resp.encoding = resp.apparent_encoding or "utf-8"
    except Exception as e:
        return jsonify({"error": f"fetch failed: {e}"}), 502

    if resp.status_code != 200:
        return jsonify({"error": f"upstream returned {resp.status_code}"}), 502

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup.select("script, style, nav, footer, header, .sidebar, .ad, .advertisement, .comment, .comments"):
        tag.decompose()

    article = soup.select_one("article") or soup.select_one(".article") or soup.select_one(".content") or soup.select_one("main") or soup.body
    text = article.get_text("\n", strip=True) if article else soup.get_text("\n", strip=True)
    import re
    text = re.sub(r'\n{3,}', '\n\n', text)
    title = soup.title.string.strip() if soup.title else "article"

    # 检测是否英文为主，自动翻译中文版
    cn_text = ""
    non_cn = sum(1 for c in text if c.isascii() and c.isalpha())
    if len(text) > 0 and non_cn / max(len(text), 1) > 0.5:
        try:
            cn_text = _translate_text(text[:8000])
        except Exception:
            cn_text = ""

    if fmt == "md":
        content = f"# {title}\n\n> 来源: {url}\n\n## 原文\n\n{text}"
        if cn_text:
            content += f"\n\n---\n\n## 中文翻译\n\n{cn_text}"
        filename = f"{title[:50]}.md"
        mimetype = "text/markdown"
    else:
        content = f"标题: {title}\n来源: {url}\n\n=== 原文 ===\n\n{text}"
        if cn_text:
            content += f"\n\n=== 中文翻译 ===\n\n{cn_text}"
        filename = f"{title[:50]}.txt"
        mimetype = "text/plain"

    from io import BytesIO
    return send_file(
        BytesIO(content.encode("utf-8")),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


# ── 软件站 ──

@app.route("/about")
def about_page():
    """TRAE 开发实践展示页"""
    return render_template("about.html")


@app.route("/platforms")
def platforms_page():
    """平台资源页 — 注入爬虫抓取的短视频真实数据"""
    sv_data = _get_shortvideo_data()
    return render_template("platforms.html", sv_data=sv_data)


@app.route("/api/shortvideo")
def api_shortvideo():
    """短视频趋势数据 API（供前端 AJAX 刷新）"""
    return jsonify(_get_shortvideo_data())


def _get_shortvideo_data():
    """从 SQLite 查询短视频爬虫数据，按平台分组"""
    try:
        rows = store.query(
            source="shortvideo_trending",
            limit=100,
            hours=72,
        )
        platforms = {}
        for row in rows:
            extra = json.loads(row.get("extra", "{}")) if isinstance(row.get("extra"), str) else row.get("extra", {})
            platform = extra.get("platform", "unknown")
            if platform not in platforms:
                platforms[platform] = []
            platforms[platform].append({
                "title": row.get("title", ""),
                "url": row.get("url", ""),
                "description": row.get("description", ""),
                "tags": row.get("tags", ""),
                "extra": extra,
                "fetched_at": row.get("fetched_at", 0),
            })
        return {"ok": True, "platforms": platforms, "count": sum(len(v) for v in platforms.values())}
    except Exception as e:
        return {"ok": False, "error": str(e), "platforms": {}, "count": 0}


@app.route("/software")
def software_page():
    return render_template("software.html")


@app.route("/agents")
def agents_page():
    return render_template("agents.html")


# ── 管理端点（本地调试用）──

@app.route("/api/v1/admin/create-key", methods=["POST"])
@require_admin
def admin_create_key():
    """管理端点: 创建新 API Key """
    data = request.get_json() or {}
    tier = data.get("tier", "free")
    name = data.get("name", "")
    if tier not in TIER_LIMITS:
        return jsonify({"error": f"Invalid tier: {tier}"}), 400
    raw_key = f"{KEY_PREFIX}{tier}_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    store.create_api_key(key_hash, raw_key[:15] + "...", tier, name)
    return jsonify({
        "api_key": raw_key,
        "tier": tier,
        "name": name,
        "warning": "Store this key securely. It will NOT be shown again.",
    })



@app.route("/api/v1/admin/keys", methods=["GET"])
@require_admin
def admin_list_keys():
    """管理端点: 列出所有 Key（不返回原始 Key，只返回哈希前缀+元数据）"""
    keys = []
    for k in store.list_all_api_keys():
        keys.append({
            "hash_prefix": k.get("key_prefix", ""),
            "tier": k["tier"],
            "name": k.get("name", ""),
            "created": k.get("created_at", ""),
            "daily_used": k.get("daily_used", 0),
        })
    return jsonify({"keys": keys, "total": len(keys)})

@app.route("/")
def index():
    return render_template("landing.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", admin_key=ADMIN_KEY)


@app.route("/demo")
def demo():
    demo_key = _get_or_create_demo_key()
    return render_template("demo.html", demo_key=demo_key)


@app.route("/console")
def console_page():
    demo_key = _get_or_create_demo_key()
    return render_template("console.html", demo_key=demo_key, admin_key=ADMIN_KEY, sources=SOURCE_LABELS)


@app.route("/github")
def github_page():
    return render_template("github.html")


@app.route("/finance")
def finance_page():
    """金融页 — 注入爬虫抓取的真实金融数据"""
    fin_data = _get_finance_data()
    return render_template("finance.html", fin_data=fin_data)


@app.route("/api/finance")
def api_finance():
    """金融数据 API（供前端 AJAX 刷新）"""
    return jsonify(_get_finance_data())


def _get_finance_data():
    """从 SQLite 查询金融爬虫数据，按类型分组"""
    try:
        rows = store.query(
            source="finance_data",
            limit=200,
            hours=48,
        )
        stocks = []
        sectors = []
        indices = []
        for row in rows:
            extra = json.loads(row.get("extra", "{}")) if isinstance(row.get("extra"), str) else row.get("extra", {})
            dtype = extra.get("type", "")
            item = {
                "title": row.get("title", ""),
                "url": row.get("url", ""),
                "extra": extra,
                "fetched_at": row.get("fetched_at", 0),
            }
            if dtype == "stock":
                stocks.append(item)
            elif dtype == "sector":
                sectors.append(item)
            elif dtype == "index":
                indices.append(item)
        return {
            "ok": True,
            "stocks": stocks,
            "sectors": sectors,
            "indices": indices,
            "count": len(stocks) + len(sectors) + len(indices),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "stocks": [], "sectors": [], "indices": [], "count": 0}


@app.route("/visual")
def visual_page():
    return render_template("visual.html")


@app.route("/agent-deploy")
def agent_deploy_page():
    return render_template("agent_deploy.html", has_access=True)


@app.route("/script-market")
def script_market_page():
    return render_template("script_market.html")


@app.route("/docs")
def docs():
    return render_template("docs.html")


@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


@app.route("/pay")
def pay():
    """支付页面 — 演示模式，重定向到定价页"""
    tier = request.args.get("tier", "")
    return render_template("pricing.html", selected_tier=tier)


@app.route("/user")
def user():
    """用户中心 — 演示模式，重定向到控制台"""
    return redirect("/console")


@app.route("/favicon.ico")
def favicon():
    """返回空的 favicon 防止 404"""
    from io import BytesIO
    return send_file(
        BytesIO(b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
        mimetype="image/x-icon",
    )


@app.route("/api/stats")
@require_admin
def api_stats():
    raw = store.stats()
    sources = {}
    for key, val in raw.get("sources", {}).items():
        sources[SOURCE_LABELS.get(key, key)] = val
    return jsonify({"total": raw["total"], "sources": sources})


@app.route("/api/source-labels")
@require_admin
def api_source_labels():
    """返回来源 ID → 中文名 映射 + 标签映射"""
    return jsonify({
        "sources": SOURCE_LABELS,
        "tags": TAG_LABELS,
    })


@app.route("/api/items")
@require_admin
def api_items():
    source = request.args.get("source", "")
    tag = request.args.get("tag", "")
    keyword = request.args.get("keyword", "")
    hours = request.args.get("hours", type=int)
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    # 如果按中文来源名筛选，反查 ID
    source_id = None
    if source:
        for sid, label in SOURCE_LABELS.items():
            if label == source:
                source_id = sid
                break
        if source_id is None:
            source_id = source

    # 当有关键词时，先过滤再分页，确保分页结果正确
    if keyword:
        kw = keyword.lower()
        all_rows = store.query(source=source_id or None, tag=tag or None, hours=hours, limit=10000)
        all_rows = [r for r in all_rows if kw in r.get("title","").lower() or kw in r.get("description","").lower()]
        total = len(all_rows)
        items = all_rows[offset:offset + limit]
        has_more = offset + limit < total
    else:
        rows = store.query(
            source=source_id or None,
            tag=tag or None,
            hours=hours,
            limit=limit + 1,
            offset=offset,
        )
        has_more = len(rows) > limit
        items = rows[:limit]
        if source_id or tag or hours:
            all_rows = store.query(source=source_id or None, tag=tag or None, hours=hours, limit=10000)
            total = len(all_rows)
        else:
            total = store.stats()["total"]

    for r in items:
        r["source_label"] = SOURCE_LABELS.get(r.get("source",""), r.get("source",""))
        if isinstance(r.get("extra"), str):
            try:
                r["extra"] = json.loads(r["extra"])
            except json.JSONDecodeError:
                r["extra"] = {}

    return jsonify({"items": items, "total": total, "has_more": has_more})


@app.route("/api/filters")
@require_admin
def api_filters():
    stats = store.stats()
    sources = [SOURCE_LABELS.get(k, k) for k in stats.get("sources", {}).keys()]
    rows = store.conn.execute("SELECT DISTINCT tags FROM items WHERE tags != ''").fetchall()
    tags_set = set()
    for r in rows:
        for t in r[0].split(","):
            t = t.strip()
            if t:
                tags_set.add(TAG_LABELS.get(t, t))
    return jsonify({"sources": sources, "tags": sorted(tags_set)})


@app.route("/api/read")
@require_admin
def api_read():
    """服务端抓取文章全文，返回清洗后的内容"""
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "缺少 url 参数"}), 400

    # SSRF protection: validate URL before fetching
    from urllib.parse import urlparse
    import socket
    import ipaddress

    parsed = urlparse(url)
    if parsed.scheme not in ("https",):
        return jsonify({"error": "仅支持 https:// 协议"}), 400

    hostname = parsed.hostname or ""
    if not hostname:
        return jsonify({"error": "无法解析主机名"}), 400

    # Block private/reserved IPs
    private_ranges = [
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("0.0.0.0/8"),
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
        ipaddress.ip_network("fe80::/10"),
    ]
    try:
        addr = socket.getaddrinfo(hostname, None)[0][4][0]
        ip = ipaddress.ip_address(addr)
        for r in private_ranges:
            if ip in r:
                return jsonify({"error": "禁止访问内网地址"}), 403
    except (socket.gaierror, ValueError):
        return jsonify({"error": "无法解析目标主机"}), 400

    proxy = config.get("proxy", "")
    proxies = {"http": proxy, "https": proxy} if proxy else None

    resp = None
    last_error = ""

    # 策略1: curl_cffi + 代理 (绕过 Cloudflare)
    if proxy:
        try:
            resp = cffi_requests.get(url, impersonate="chrome", timeout=20, proxies=proxies)
        except Exception as e:
            last_error = str(e)[:100]

    # 策略2: curl_cffi 直连
    if resp is None or resp.status_code != 200:
        try:
            resp = cffi_requests.get(url, impersonate="chrome", timeout=20)
        except Exception as e:
            last_error = str(e)[:100]

    # 策略3: requests + 代理
    if resp is None or resp.status_code != 200:
        try:
            import requests as req
            s = req.Session()
            s.trust_env = False
            if proxy:
                s.proxies = proxies
            resp = s.get(url, timeout=20, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
        except Exception as e:
            last_error = str(e)[:100]

    # 策略4: requests 直连
    if resp is None or resp.status_code != 200:
        try:
            import requests as req
            s = req.Session()
            s.trust_env = False
            resp = s.get(url, timeout=20, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
        except Exception as e:
            last_error = str(e)[:100]

    if resp is None:
        return jsonify({"error": f"无法连接: {last_error}"}), 502

    if resp.status_code != 200:
        return jsonify({"error": f"HTTP {resp.status_code}"}), 502

    try:
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        title = ""
        for tag_name in ["h1", "h2"]:
            t = soup.find(tag_name)
            if t and t.get_text(strip=True):
                title = t.get_text(strip=True)[:200]
                break
        if not title:
            title = soup.title.string.strip() if soup.title else ""

        for tag in soup.select("script, style, nav, footer, header, aside, .sidebar, .comments, .ads, .nav, .footer, .header, .menu, .related, .recommend, .share, .social, iframe, noscript"):
            tag.decompose()

        content_el = soup.find("article") or soup.find("main") or soup.find("body")
        if not content_el:
            return jsonify({"error": "无法提取正文"}), 500

        parts = []
        for el in content_el.select("p, h1, h2, h3, h4, h5, h6, pre, blockquote, ul, ol, figure, img, table"):
            if el.name in ("h1","h2","h3","h4","h5","h6"):
                text = el.get_text(strip=True)
                if len(text) > 5:
                    parts.append(f'<{el.name} class="rh">{text}</{el.name}>')
            elif el.name == "p":
                text = el.get_text(strip=True)
                if len(text) > 20:
                    parts.append(f"<p>{text}</p>")
            elif el.name == "pre":
                code = el.get_text()
                if len(code) > 10:
                    parts.append(f"<pre><code>{_escape(code[:5000])}</code></pre>")
            elif el.name == "blockquote":
                text = el.get_text(strip=True)
                if len(text) > 10:
                    parts.append(f"<blockquote>{text}</blockquote>")
            elif el.name in ("ul","ol"):
                items = "".join(f"<li>{li.get_text(strip=True)}</li>" for li in el.select("li")[:20])
                if items:
                    parts.append(f"<{el.name}>{items}</{el.name}>")
            elif el.name == "img":
                src = el.get("src","") or el.get("data-src","")
                if src:
                    parts.append(f'<img src="{_escape(src)}" style="max-width:100%">')
            elif el.name == "figure":
                img = el.find("img")
                caption = el.find("figcaption")
                if img:
                    src = img.get("src","") or img.get("data-src","")
                    cap_text = caption.get_text(strip=True) if caption else ""
                    if src:
                        parts.append(f'<figure><img src="{_escape(src)}" style="max-width:100%"><figcaption>{cap_text}</figcaption></figure>')

        content = "\n".join(parts) if parts else "<p>未能提取到正文内容，请<a href='" + _escape(url) + "' target='_blank'>查看原文</a></p>"

        return jsonify({
            "title": title,
            "content": content,
            "url": url,
        })

    except Exception as e:
        return jsonify({"error": f"抓取失败: {str(e)[:200]}"}), 500


def _escape(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


# ── 翻译引擎 ──
GOOGLE_TRANSLATE = "https://translate.googleapis.com/translate_a/single"

def _translate_text(text: str, target: str = "zh-CN") -> str:
    """使用 Google Translate 将文本翻译为中文"""
    if not text or not text.strip():
        return text
    # 检测是否已经是中文为主
    chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
    if chinese_chars > len(text) * 0.5:
        return text  # 已经是中文，不翻译

    proxy = config.get("proxy", "")
    proxies = {"http": proxy, "https": proxy} if proxy else None

    # 分段翻译（每段最多 1500 字符）
    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) > 1500:
            if current:
                chunks.append(current)
            current = line
        else:
            current += "\n" + line if current else line
    if current:
        chunks.append(current)

    results = []
    for chunk in chunks[:10]:  # 最多 10 段
        try:
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": target,
                "dt": "t",
                "q": chunk,
            }
            resp = None
            # 尝试策略
            for strategy in [
                lambda: cffi_requests.get(GOOGLE_TRANSLATE, params=params, timeout=15, proxies=proxies),
                lambda: cffi_requests.get(GOOGLE_TRANSLATE, params=params, timeout=15),
            ]:
                try:
                    resp = strategy()
                    if resp.status_code == 200:
                        break
                except Exception:
                    continue

            if not resp or resp.status_code != 200:
                import requests as req
                s = req.Session()
                s.trust_env = False
                if proxy:
                    s.proxies = proxies
                resp = s.get(GOOGLE_TRANSLATE, params=params, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                # Google Translate 返回格式: [[["译文","原文",...]],...]
                translated = "".join(
                    part[0] for part in data[0] if part[0] is not None
                )
                results.append(translated)
            else:
                results.append(chunk)  # 翻译失败保留原文
        except Exception:
            results.append(chunk)

    return "\n".join(results)


@app.route("/api/translate", methods=["POST"])
@require_admin
def api_translate():
    """翻译文本为中文"""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "缺少 text"}), 400
    try:
        translated = _translate_text(text)
        return jsonify({"text": text, "translated": translated})
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


# ── 全局 Monitor 引用 (入口处注入) ──
_monitor = None
_fetching = True


@app.route("/api/fetch", methods=["POST"])
@require_admin
def api_fetch():
    """手动触发一轮抓取"""
    if _monitor:
        _monitor.run_once()
        return jsonify({"ok": True, "total": store.stats()["total"]})
    return jsonify({"error": "监控未启动"}), 503


@app.route("/api/toggle-fetch", methods=["POST"])
@require_admin
def api_toggle_fetch():
    """暂停/恢复自动抓取"""
    global _fetching
    data = request.get_json(silent=True) or {}
    _fetching = data.get("fetching", True)
    if _monitor:
        if _fetching:
            _monitor.resume()
        else:
            _monitor.pause()
    return jsonify({"fetching": _fetching})


# ── 后台监控调度 ──

# ── 启动时迁移 api_keys.json → SQLite ──
store.migrate_keys_from_json(API_KEYS_FILE)

class Monitor:
    def __init__(self, config: dict):
        self.cfg = config
        self.proxy = config.get("proxy", "")
        self.notifier = Notifier()
        self.intervals = config.get("intervals", {})
        self.fetchers = {}
        self._init_fetchers()

    def _init_fetchers(self):
        cfg = self.cfg
        if cfg.get("github_trending", {}).get("enabled", True):
            self.fetchers["github_trending"] = GitHubTrendingFetcher(
                proxy=self.proxy,
                languages=cfg["github_trending"].get("languages", [""]),
                since=cfg["github_trending"].get("since", ["daily"]),
                spoken_language=cfg["github_trending"].get("spoken_language", ""),
            )
        if cfg.get("hackernews", {}).get("enabled", True):
            self.fetchers["hackernews"] = HackerNewsFetcher(
                proxy=self.proxy,
                max_items=cfg["hackernews"].get("max_items", 30),
            )
        rss_feeds = cfg.get("rss_feeds", [])
        if rss_feeds:
            self.fetchers["rss"] = RSSFetcherWithProxy(proxy=self.proxy, feeds=rss_feeds)
        cffi_feeds = cfg.get("curl_cffi_feeds", [])
        if cffi_feeds:
            self.fetchers["curl_cffi_rss"] = CurlCffiRSSFetcher(proxy=self.proxy, feeds=cffi_feeds)
        if cfg.get("nvd_cve", {}).get("enabled", True):
            self.fetchers["nvd_cve"] = NVDCVEFetcher(
                days_back=cfg["nvd_cve"].get("days_back", 7),
                max_results=cfg["nvd_cve"].get("max_results", 20),
            )
        if cfg.get("shortvideo_trending", {}).get("enabled", True):
            self.fetchers["shortvideo_trending"] = ShortVideoTrendingFetcher(
                proxy=self.proxy,
                max_per_platform=cfg["shortvideo_trending"].get("max_per_platform", 20),
            )
        if cfg.get("finance_data", {}).get("enabled", True):
            self.fetchers["finance_data"] = FinanceDataFetcher(
                proxy=self.proxy,
                max_stocks=cfg["finance_data"].get("max_stocks", 50),
            )

    def pause(self):
        if hasattr(self, '_scheduler') and self._scheduler:
            self._scheduler.pause()

    def resume(self):
        if hasattr(self, '_scheduler') and self._scheduler:
            self._scheduler.resume()

    def run_once(self):
        print(f"\n{'─'*40}\n  [{datetime.now().strftime('%H:%M:%S')}] 抓取轮次\n{'─'*40}")
        total_new = 0
        for name, fetcher in self.fetchers.items():
            print(f"  [{name}] 抓取中...")
            try:
                items = fetcher.fetch()
                new_count = 0
                for item in items:
                    if store.upsert(
                        source=name, title=item.get("title",""),
                        url=item.get("url",""), description=item.get("description",""),
                        tags=item.get("tags",[]), extra=item.get("extra",{}),
                    ):
                        new_count += 1
                label = SOURCE_LABELS.get(name, name)
                print(f"  [{label}] {len(items)} 条, +{new_count} 新")
                total_new += new_count
            except Exception as e:
                print(f"  [{name}] 错误: {e}")
        if total_new:
            self.notifier.send(
                title=f"{total_new} 条新内容",
                body=f"本轮发现 {total_new} 条新条目",
                items=[SOURCE_LABELS.get(n, n) for n in self.fetchers],
            )
        store.cleanup_old()
        print(f"  [完成] +{total_new}, 总计 {store.stats()['total']} 条")

    def _job_wrapper(self, name, fetcher):
        print(f"\n  [{SOURCE_LABELS.get(name, name)}] 定时触发")
        try:
            items = fetcher.fetch()
            new_count = 0
            for item in items:
                if store.upsert(
                    source=name, title=item.get("title",""),
                    url=item.get("url",""), description=item.get("description",""),
                    tags=item.get("tags",[]), extra=item.get("extra",{}),
                ):
                    new_count += 1
            print(f"  [{SOURCE_LABELS.get(name, name)}] {len(items)} 条, +{new_count} 新")
            if new_count > 10:
                self.notifier.send(
                    title=f"[{SOURCE_LABELS.get(name, name)}] {new_count} 条新内容",
                    items=[item.get("title","") for item in items[:5]],
                )
        except Exception as e:
            print(f"  [{name}] 错误: {e}")

    def start(self, run_first=False):
        self._scheduler = BackgroundScheduler()
        for name, fetcher in self.fetchers.items():
            minutes = self.intervals.get(name, 60)
            self._scheduler.add_job(
                func=self._job_wrapper,
                trigger=IntervalTrigger(minutes=minutes),
                args=[name, fetcher], id=name, name=name, replace_existing=True,
            )
            print(f"  [{SOURCE_LABELS.get(name, name)}] 每 {minutes} 分钟")
        self._scheduler.start()
        print(f"  调度器已启动 ({len(self.fetchers)} 个任务)\n")
        if run_first:
            self.run_once()
        return self._scheduler


# ── 入口 ──

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="统一事件监视器")
    parser.add_argument("--no-fetch", action="store_true", help="仅启动 Web 面板，不抓取")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5889)), help="Web 面板端口")
    args = parser.parse_args()

    _monitor = Monitor(config)

    if not args.no_fetch:
        _monitor.start()
        print(f"\n  Web 面板: http://localhost:{args.port}\n")
        # 把首次全量抓取放到后台线程，不阻塞 Flask 启动
        import threading
        threading.Thread(target=_monitor.run_once, daemon=True).start()
    else:
        print(f"\n  Web 面板 (仅浏览): http://localhost:{args.port}\n")

    try:
        app.run(host="0.0.0.0", port=args.port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n  已停止")
        store.close()
