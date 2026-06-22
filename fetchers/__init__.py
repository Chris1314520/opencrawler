"""基础抓取器 + HTTP 客户端（自动处理代理）"""

import time
import requests
from abc import ABC, abstractmethod


class BaseFetcher(ABC):
    def __init__(self, proxy: str = ""):
        self.session = requests.Session()
        self.session.trust_env = False  # 不继承系统代理，避免代理不可达导致所有请求失败
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html, */*",
        })
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self.proxy = proxy

    def _get(self, url: str, timeout: int = 30) -> requests.Response:
        return self.session.get(url, timeout=timeout)

    @abstractmethod
    def fetch(self) -> list[dict]:
        """返回 [{title, url, description, tags, extra}, ...]"""
        ...


def safe_str(s, max_len=200):
    """安全截断字符串"""
    if not s:
        return ""
    return str(s)[:max_len].strip()
