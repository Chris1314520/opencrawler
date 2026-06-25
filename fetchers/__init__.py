"""基础抓取器 + HTTP 客户端（自动重试、统一日志、curl_cffi 降级）"""

import logging
import time
import requests
from abc import ABC, abstractmethod
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """所有抓取器的基类。

    提供：
      - 预配置的 requests.Session（自动重试、连接池）
      - _get / _get_json 便捷方法
      - _fetch_with_fallback / _post_with_fallback 通用降级框架
    """

    def __init__(self, proxy: str = "", timeout: int = 30):
        self.session = requests.Session()
        self.session.trust_env = False  # 不继承系统代理，避免代理不可达导致所有请求失败
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html, */*",
        })
        # 配置 HTTP 重试
        retry = Retry(total=3, backoff_factor=0.5,
                      status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self.proxy = proxy
        self.timeout = timeout

    # ------------------------------------------------------------------
    #  基础请求方法
    # ------------------------------------------------------------------

    def _get(self, url: str, timeout: int = None, **kwargs) -> requests.Response:
        """GET 请求，支持自定义 timeout 和透传 kwargs（headers, params 等）"""
        return self.session.get(url, timeout=timeout or self.timeout, **kwargs)

    def _get_json(self, url: str, timeout: int = None, **kwargs) -> dict | None:
        """GET 请求并返回 JSON，失败返回 None"""
        try:
            resp = self._get(url, timeout=timeout, **kwargs)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("HTTP %d: %s", resp.status_code, url)
        except Exception as e:
            logger.error("请求失败 %s: %s", url, e)
        return None

    # ------------------------------------------------------------------
    #  通用降级框架（requests → curl_cffi）
    # ------------------------------------------------------------------

    def _fetch_with_fallback(self, url: str, parser_fn, timeout: int = 15,
                             **kwargs) -> list[dict]:
        """GET 请求 + curl_cffi 降级的通用抓取框架。

        parser_fn 接收 (resp_json_or_text, resp) 返回：
          - list[dict]：成功（含空列表，表示合法无数据）
          - None：信号触发降级（API 错误等）
        """
        try:
            resp = self._get(url, timeout=timeout, **kwargs)
            if resp.status_code == 200:
                data = self._extract_body(resp)
                result = parser_fn(data, resp)
                if result is not None:
                    return result
                # result is None → parser 信号：尝试降级
        except Exception as e:
            logger.warning("requests 请求失败 %s: %s", url, e)

        # curl_cffi 降级
        try:
            from curl_cffi import requests as cffi_requests
            proxy_dict = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            resp = cffi_requests.get(url, impersonate="chrome", timeout=timeout,
                                     proxies=proxy_dict, **kwargs)
            if resp.status_code == 200:
                data = self._extract_body(resp)
                result = parser_fn(data, resp)
                if result is not None:
                    return result
        except Exception as e:
            logger.warning("curl_cffi 降级也失败 %s: %s", url, e)
        return []

    def _post_with_fallback(self, url: str, parser_fn, timeout: int = 15,
                            **kwargs) -> list[dict]:
        """POST 请求 + curl_cffi 降级的通用抓取框架。

        适用于 GraphQL 等 POST 接口。kwargs 透传 json=, headers= 等。
        parser_fn 约定同 _fetch_with_fallback。
        """
        try:
            resp = self.session.post(url, timeout=timeout, **kwargs)
            if resp.status_code == 200:
                data = self._extract_body(resp)
                result = parser_fn(data, resp)
                if result is not None:
                    return result
        except Exception as e:
            logger.warning("requests POST 失败 %s: %s", url, e)

        # curl_cffi 降级
        try:
            from curl_cffi import requests as cffi_requests
            proxy_dict = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            resp = cffi_requests.post(url, impersonate="chrome", timeout=timeout,
                                      proxies=proxy_dict, **kwargs)
            if resp.status_code == 200:
                data = self._extract_body(resp)
                result = parser_fn(data, resp)
                if result is not None:
                    return result
        except Exception as e:
            logger.warning("curl_cffi POST 降级也失败 %s: %s", url, e)
        return []

    @staticmethod
    def _extract_body(resp):
        """根据 content-type 自动返回 JSON dict 或文本 str。

        某些 API 返回 JSON 但 content-type 不标准，因此做兜底尝试。
        """
        ct = resp.headers.get('content-type', '')
        if ct.startswith('application/json'):
            return resp.json()
        # 兜底：content-type 不标准时尝试 JSON 解析
        try:
            return resp.json()
        except (ValueError, TypeError):
            return resp.text

    # ------------------------------------------------------------------
    #  抽象接口
    # ------------------------------------------------------------------

    @abstractmethod
    def fetch(self) -> list[dict]:
        """返回 [{title, url, description, tags, extra}, ...]"""
        ...


def safe_str(s, max_len=200):
    """安全截断字符串"""
    if not s:
        return ""
    return str(s)[:max_len].strip()
