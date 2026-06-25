"""RSS 多源抓取器 —— 使用 feedparser，支持 requests / curl_cffi 双模式"""

import logging
import feedparser
from . import BaseFetcher, safe_str

logger = logging.getLogger(__name__)


class RSSFetcher(BaseFetcher):
    """从配置的 RSS 源抓取条目。

    参数:
        proxy:     HTTP/HTTPS 代理地址
        feeds:     RSS 源配置列表 [{"name", "url", "tags"}, ...]
        use_cffi:  True 时使用 curl_cffi（chrome 指纹）发请求，
                   适用于被 Cloudflare / 反爬保护的站点；
                   False 时使用 requests（默认）
    """

    def __init__(self, proxy: str = "", feeds: list[dict] = None,
                 use_cffi: bool = False):
        super().__init__(proxy)
        self.feeds = feeds or []
        self.use_cffi = use_cffi

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
                logger.warning("[RSS] %s 抓取失败: %s", name, e)
        return results

    # ------------------------------------------------------------------
    #  内部方法
    # ------------------------------------------------------------------

    def _fetch_one(self, name: str, url: str, tags: list) -> list[dict]:
        """抓取单个 RSS 源并解析条目。

        根据 use_cffi 选择 HTTP 客户端，解析逻辑统一。
        """
        content = self._fetch_content(name, url)
        if not content:
            return []

        fp = feedparser.parse(content)
        if fp.bozo and not fp.entries:
            logger.warning("[RSS] %s 解析错误: %s", name, fp.bozo_exception)
            return []

        items = []
        for entry in fp.entries[:20]:
            title = safe_str(entry.get("title", ""), max_len=200)
            link = entry.get("link", "")
            desc = safe_str(
                entry.get("summary", "") or entry.get("description", ""),
                max_len=500,
            )
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

    def _fetch_content(self, name: str, url: str) -> str:
        """根据 use_cffi 标志选择 HTTP 客户端获取 RSS 内容文本"""
        if self.use_cffi:
            return self._fetch_content_cffi(name, url)
        return self._fetch_content_requests(name, url)

    def _fetch_content_requests(self, name: str, url: str) -> str:
        """使用 requests 获取 RSS 内容"""
        try:
            resp = self._get(url, timeout=30)
            if resp.status_code != 200:
                logger.warning("[RSS] %s HTTP %d", name, resp.status_code)
                return ""
            return resp.text
        except Exception as e:
            logger.warning("[RSS] %s 请求失败: %s", name, e)
            return ""

    def _fetch_content_cffi(self, name: str, url: str) -> str:
        """使用 curl_cffi（chrome 指纹）获取 RSS 内容，绕过 TLS 检测"""
        try:
            from curl_cffi import requests as cffi_requests
            proxy_dict = (
                {"http": self.proxy, "https": self.proxy}
                if self.proxy else None
            )
            resp = cffi_requests.get(
                url, impersonate="chrome", timeout=30, proxies=proxy_dict,
            )
            if resp.status_code != 200:
                logger.warning("[RSS] %s HTTP %d (curl_cffi)", name, resp.status_code)
                return ""
            return resp.text
        except Exception as e:
            logger.warning("[RSS] %s curl_cffi 请求失败: %s", name, e)
            return ""
