"""Hacker News 抓取器 —— 通过官方 Firebase API"""

import time
from . import BaseFetcher


class HackerNewsFetcher(BaseFetcher):
    API_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
    API_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"

    def __init__(self, proxy: str = "", max_items: int = 30):
        super().__init__(proxy)
        self.max_items = max_items

    def fetch(self) -> list[dict]:
        try:
            resp = self._get(self.API_TOP, timeout=15)
            if resp.status_code != 200:
                print(f"  [HN] 获取列表 HTTP {resp.status_code}")
                return []
            ids = resp.json()[:self.max_items]
        except Exception as e:
            print(f"  [HN] 获取列表失败: {e}")
            return []

        results = []
        for i, item_id in enumerate(ids):
            if i > 0:
                time.sleep(0.1)  # 避免触发 Firebase 限流
            try:
                item = self._fetch_item(item_id)
                if item:
                    results.append(item)
            except Exception as e:
                print(f"  [HN] 条目 {item_id} 失败: {e}")
        return results

    def _fetch_item(self, item_id: int) -> dict | None:
        url = self.API_ITEM.format(item_id)
        try:
            resp = self._get(url, timeout=15)
        except Exception:
            return None
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data or data.get("type") != "story":
            return None

        title = data.get("title", "")
        item_url = data.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
        score = data.get("score", 0)
        by = data.get("by", "")
        descendants = data.get("descendants", 0)

        return {
            "title": title,
            "url": item_url,
            "description": f"{score} points by {by} | {descendants} comments",
            "tags": ["HackerNews"],
            "extra": {
                "score": score,
                "author": by,
                "comments": descendants,
                "hn_id": item_id,
            },
        }
