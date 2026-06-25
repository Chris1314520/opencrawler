"""Hacker News 抓取器 —— 通过官方 Firebase API，并发获取条目详情"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import BaseFetcher

logger = logging.getLogger(__name__)


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
                logger.warning("[HN] 获取列表 HTTP %d", resp.status_code)
                return []
            ids = resp.json()[:self.max_items]
        except Exception as e:
            logger.error("[HN] 获取列表失败: %s", e)
            return []

        # 并发获取 item 详情（max_workers=5 控制并发度，避免触发限流）
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_id = {
                executor.submit(self._fetch_item, item_id): item_id
                for item_id in ids
            }
            for future in as_completed(future_to_id):
                item_id = future_to_id[future]
                try:
                    item = future.result()
                    if item:
                        results.append(item)
                except Exception as e:
                    logger.warning("[HN] 条目 %s 失败: %s", item_id, e)

        # 按原始顺序排序（as_completed 返回顺序不确定）
        results.sort(key=lambda x: ids.index(x["extra"]["hn_id"]))
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
