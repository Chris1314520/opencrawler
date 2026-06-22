"""curl_cffi RSS 抓取器 —— 绕过 TLS 指纹检测（Cloudflare 等）"""

import feedparser
from curl_cffi import requests as cffi_requests
from . import safe_str


class CurlCffiRSSFetcher:
    """使用 curl_cffi 伪装的 RSS 抓取器，适用于被 Cloudflare/反爬保护的站点"""

    def __init__(self, proxy: str = "", feeds: list[dict] = None):
        self.proxy = proxy
        self.feeds = feeds or []

    def fetch(self) -> list[dict]:
        results = []
        for feed_cfg in self.feeds:
            name = feed_cfg.get("name", "Unknown")
            url = feed_cfg.get("url", "")
            tags = feed_cfg.get("tags", [])
            if not url:
                continue
            try:
                items = self._fetch_one(name, url, tags)
                results.extend(items)
            except Exception as e:
                print(f"  [cRSS] {name} 抓取失败: {e}")
        return results

    def _fetch_one(self, name: str, url: str, tags: list) -> list[dict]:
        proxy_dict = {"http": self.proxy, "https": self.proxy} if self.proxy else None

        try:
            resp = cffi_requests.get(
                url,
                impersonate="chrome",
                timeout=30,
                proxies=proxy_dict,
            )
        except Exception as e:
            print(f"  [cRSS] {name} 请求失败: {e}")
            return []

        if resp.status_code != 200:
            print(f"  [cRSS] {name} HTTP {resp.status_code}")
            return []

        fp = feedparser.parse(resp.text)
        if fp.bozo and not fp.entries:
            print(f"  [cRSS] {name} 解析错误: {fp.bozo_exception}")
            return []

        items = []
        for entry in fp.entries[:20]:
            title = safe_str(entry.get("title", ""), max_len=200)
            link = entry.get("link", "")
            desc = safe_str(entry.get("summary", "") or entry.get("description", ""), max_len=500)
            published = entry.get("published", "") or entry.get("updated", "")

            items.append({
                "title": title,
                "url": link,
                "description": desc,
                "tags": ["RSS", name] + tags,
                "extra": {
                    "feed_name": name,
                    "published": published,
                },
            })
        return items
