"""RSS 多源抓取器 —— 使用 feedparser"""

import time
import feedparser
from . import BaseFetcher, safe_str


class RSSFetcher(BaseFetcher):
    """从配置的 RSS 源抓取条目"""

    def __init__(self, proxy: str = "", feeds: list[dict] = None):
        super().__init__(proxy)
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
                print(f"  [RSS] {name} 抓取失败: {e}")
        return results

    def _fetch_one(self, name: str, url: str, tags: list) -> list[dict]:
        try:
            resp = self._get(url, timeout=30)
            if resp.status_code != 200:
                print(f"  [RSS] {name} HTTP {resp.status_code}")
                return []
            content = resp.text
        except Exception as e:
            print(f"  [RSS] {name} 请求失败: {e}")
            return []

        fp = feedparser.parse(content)
        if fp.bozo and not fp.entries:
            print(f"  [RSS] {name} 解析错误: {fp.bozo_exception}")
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


class RSSFetcherWithProxy(RSSFetcher):
    """带代理的 RSS 抓取器 —— 与 RSSFetcher 行为一致，通过 requests 获取内容再用 feedparser 解析"""
