"""curl_cffi RSS 抓取器 —— 已合并到 rss_feeds.py，保留导入兼容

历史代码中 CurlCffiRSSFetcher 默认使用 curl_cffi 发请求，
此兼容层保持相同行为（use_cffi=True）。
"""

from .rss_feeds import RSSFetcher


class CurlCffiRSSFetcher(RSSFetcher):
    """兼容旧接口：默认使用 curl_cffi 绕过 TLS 指纹检测。

    等价于 RSSFetcher(proxy=..., feeds=..., use_cffi=True)
    """

    def __init__(self, proxy: str = "", feeds: list[dict] = None):
        super().__init__(proxy=proxy, feeds=feeds, use_cffi=True)
