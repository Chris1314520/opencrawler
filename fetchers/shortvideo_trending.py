"""短视频热门抓取器 —— B站/抖音/快手/小红书/视频号 热门内容聚合

覆盖平台：
  - B站（Bilibili）：公开热门视频 API，获取真实 BV 号链接（最重要）
  - 抖音：热搜词榜单 API（主 + 备选）
  - 快手：GraphQL 热门视频接口
  - 小红书：尝试公开页面数据（失败则跳过）
  - 视频号：无公开 API，直接跳过

统一返回格式：
  [{title, url, description, tags, extra:{platform, video_url, author,
    views, likes, favorites, comments, duration, rank}}, ...]
"""

import json
import re
import logging
from urllib.parse import quote

from . import BaseFetcher, safe_str

try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False

logger = logging.getLogger(__name__)


class ShortVideoTrendingFetcher(BaseFetcher):
    """短视频平台热门内容聚合抓取器

    继承 BaseFetcher，使用 requests.Session 发起请求；
    当遇到 TLS 指纹检测 / 反爬时，自动降级到 curl_cffi（chrome 指纹）。
    """

    SOURCE = "shortvideo_trending"

    # ── API 端点 ──
    BILIBILI_POPULAR = "https://api.bilibili.com/x/web-interface/popular"
    DOUYIN_HOTSEARCH = "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/"
    DOUYIN_HOTSEARCH_BACKUP = "https://www.douyin.com/aweme/v1/web/hot/searchlist/"
    KUAISHOU_GRAPHQL = "https://www.kuaishou.com/graphql"
    XHS_EXPLORE = "https://www.xiaohongshu.com/explore"

    def __init__(self, proxy: str = "", max_per_platform: int = 20):
        super().__init__(proxy)
        self.max_per_platform = max_per_platform
        # B站 API 需要 Referer 才能正常返回数据
        self.session.headers.update({
            "Referer": "https://www.bilibili.com/",
            "Origin": "https://www.bilibili.com",
        })

    # ════════════════════════════════════════════════════════════
    #  主入口
    # ════════════════════════════════════════════════════════════

    def fetch(self) -> list[dict]:
        """抓取所有短视频平台热门内容，返回统一格式列表"""
        results = []

        # 1. B站（最重要，有公开 API，获取真实 BV 号视频链接）
        print("  [短视频/B站] 抓取中...")
        results.extend(self._fetch_bilibili())

        # 2. 抖音热搜
        print("  [短视频/抖音] 抓取中...")
        results.extend(self._fetch_douyin())

        # 3. 快手热门
        print("  [短视频/快手] 抓取中...")
        results.extend(self._fetch_kuaishou())

        # 4. 小红书（尝试公开页面数据，失败则跳过）
        print("  [短视频/小红书] 抓取中...")
        results.extend(self._fetch_xiaohongshu())

        # 5. 视频号（无公开 API，跳过）
        print("  [短视频/视频号] 无公开 API，跳过")
        logger.info("[视频号] 无公开 API，跳过")

        print(f"  [短视频] 共获取 {len(results)} 条")
        return results

    # ════════════════════════════════════════════════════════════
    #  B站（Bilibili）—— 公开热门视频 API
    # ════════════════════════════════════════════════════════════

    def _fetch_bilibili(self) -> list[dict]:
        """B站热门视频：通过公开 API 获取真实 BV 号视频链接"""
        url = f"{self.BILIBILI_POPULAR}?ps={self.max_per_platform}&pn=1"

        try:
            resp = self._get(url, timeout=15)
            if resp.status_code != 200:
                print(f"  [B站] HTTP {resp.status_code}")
                if HAS_CFFI:
                    return self._fetch_bilibili_cffi()
                return []

            data = resp.json()
            if data.get("code") != 0:
                print(f"  [B站] API 返回错误: code={data.get('code')}, "
                      f"msg={data.get('message')}")
                if HAS_CFFI:
                    return self._fetch_bilibili_cffi()
                return []

            video_list = data.get("data", {}).get("list", [])
            if not video_list:
                print("  [B站] 未获取到视频列表")
                return []

            items = []
            for rank, video in enumerate(video_list[:self.max_per_platform], 1):
                bvid = video.get("bvid", "")
                if not bvid:
                    continue

                title = safe_str(video.get("title", ""), max_len=200)
                # 真实视频链接（BV 号）
                video_url = (
                    video.get("short_link")
                    or f"https://www.bilibili.com/video/{bvid}"
                )

                owner = video.get("owner", {})
                author = safe_str(owner.get("name", ""), max_len=100)

                stat = video.get("stat", {})
                views = stat.get("view", 0)
                likes = stat.get("like", 0)
                favorites = stat.get("favorite", 0)
                comments = stat.get("reply", 0)

                duration = video.get("duration", 0)  # 秒
                tname = video.get("tname", "")  # 分区名

                desc = (f"UP主: {author} | 播放: {self._fmt_num(views)} | "
                        f"点赞: {self._fmt_num(likes)} | "
                        f"收藏: {self._fmt_num(favorites)}")

                tags = ["B站", "短视频", "热门"]
                if tname:
                    tags.append(tname)

                items.append({
                    "title": title,
                    "url": video_url,
                    "description": desc,
                    "tags": tags,
                    "extra": {
                        "platform": "bilibili",
                        "video_url": video_url,
                        "author": author,
                        "views": views,
                        "likes": likes,
                        "favorites": favorites,
                        "comments": comments,
                        "duration": duration,
                        "rank": rank,
                        "bvid": bvid,
                        "category": tname,
                    },
                })

            print(f"  [B站] 获取 {len(items)} 条热门视频")
            return items

        except Exception as e:
            print(f"  [B站] 抓取失败: {e}")
            logger.exception("[B站] 抓取异常")
            if HAS_CFFI:
                return self._fetch_bilibili_cffi()
            return []

    def _fetch_bilibili_cffi(self) -> list[dict]:
        """使用 curl_cffi 抓取 B站热门（备选方案，绕过反爬）"""
        url = f"{self.BILIBILI_POPULAR}?ps={self.max_per_platform}&pn=1"
        proxy_dict = {"http": self.proxy, "https": self.proxy} if self.proxy else None

        try:
            resp = cffi_requests.get(
                url,
                impersonate="chrome",
                timeout=15,
                proxies=proxy_dict,
                headers={
                    "Referer": "https://www.bilibili.com/",
                    "Origin": "https://www.bilibili.com",
                },
            )
            if resp.status_code != 200:
                print(f"  [B站/cffi] HTTP {resp.status_code}")
                return []

            data = resp.json()
            if data.get("code") != 0:
                print(f"  [B站/cffi] API 错误: {data.get('message')}")
                return []

            video_list = data.get("data", {}).get("list", [])
            items = []
            for rank, video in enumerate(video_list[:self.max_per_platform], 1):
                bvid = video.get("bvid", "")
                if not bvid:
                    continue

                title = safe_str(video.get("title", ""), max_len=200)
                video_url = f"https://www.bilibili.com/video/{bvid}"
                owner = video.get("owner", {})
                stat = video.get("stat", {})
                author = safe_str(owner.get("name", ""), max_len=100)

                items.append({
                    "title": title,
                    "url": video_url,
                    "description": (f"UP主: {author} | "
                                    f"播放: {self._fmt_num(stat.get('view', 0))}"),
                    "tags": ["B站", "短视频", "热门"],
                    "extra": {
                        "platform": "bilibili",
                        "video_url": video_url,
                        "author": author,
                        "views": stat.get("view", 0),
                        "likes": stat.get("like", 0),
                        "favorites": stat.get("favorite", 0),
                        "comments": stat.get("reply", 0),
                        "duration": video.get("duration", 0),
                        "rank": rank,
                        "bvid": bvid,
                    },
                })

            print(f"  [B站/cffi] 获取 {len(items)} 条")
            return items

        except Exception as e:
            print(f"  [B站/cffi] 备选方案失败: {e}")
            logger.exception("[B站/cffi] 抓取异常")
            return []

    # ════════════════════════════════════════════════════════════
    #  抖音热搜
    # ════════════════════════════════════════════════════════════

    def _fetch_douyin(self) -> list[dict]:
        """抖音热搜：获取热搜词和热度值（主 API → 备选 API → curl_cffi）"""
        # 尝试主 API
        items = self._fetch_douyin_api(self.DOUYIN_HOTSEARCH)
        if items:
            return items

        # 尝试备选 API
        print("  [抖音] 主 API 失败，尝试备选 API...")
        items = self._fetch_douyin_api(self.DOUYIN_HOTSEARCH_BACKUP)
        if items:
            return items

        # 尝试 curl_cffi
        if HAS_CFFI:
            print("  [抖音] 尝试 curl_cffi...")
            items = self._fetch_douyin_cffi()
            if items:
                return items

        print("  [抖音] 所有方案均失败")
        return []

    def _fetch_douyin_api(self, api_url: str) -> list[dict]:
        """通过指定 API 获取抖音热搜词列表"""
        try:
            resp = self._get(api_url, timeout=15)
            if resp.status_code != 200:
                print(f"  [抖音] HTTP {resp.status_code} for {api_url}")
                return []

            data = resp.json()
            # 不同 API 返回结构可能不同，兼容多种格式
            word_list = (
                data.get("data", {}).get("word_list")
                or data.get("word_list")
                or data.get("data", {}).get("list")
                or []
            )

            if not word_list:
                print("  [抖音] 未获取到热搜词列表")
                return []

            items = []
            for rank, word_data in enumerate(word_list[:self.max_per_platform], 1):
                word = (
                    word_data.get("word")
                    or word_data.get("keyword")
                    or word_data.get("title")
                    or ""
                )
                if not word:
                    continue

                word = safe_str(word, max_len=200)
                hot_value = (
                    word_data.get("hot_value", 0)
                    or word_data.get("score", 0)
                    or 0
                )
                # 搜索链接（抖音搜索页）
                search_url = f"https://www.douyin.com/search/{quote(word)}"

                desc = f"热度: {self._fmt_num(hot_value)} | 排名: #{rank}"

                items.append({
                    "title": word,
                    "url": search_url,
                    "description": desc,
                    "tags": ["抖音", "短视频", "热搜"],
                    "extra": {
                        "platform": "douyin",
                        "video_url": search_url,
                        "author": "",
                        "views": hot_value,
                        "likes": 0,
                        "favorites": 0,
                        "comments": 0,
                        "duration": 0,
                        "rank": rank,
                        "hot_value": hot_value,
                        "type": "hot_search",
                    },
                })

            print(f"  [抖音] 获取 {len(items)} 条热搜词")
            return items

        except Exception as e:
            print(f"  [抖音] API 请求失败 ({api_url}): {e}")
            logger.exception("[抖音] 抓取异常")
            return []

    def _fetch_douyin_cffi(self) -> list[dict]:
        """使用 curl_cffi 抓取抖音热搜（备选方案）"""
        proxy_dict = {"http": self.proxy, "https": self.proxy} if self.proxy else None

        for api_url in [self.DOUYIN_HOTSEARCH, self.DOUYIN_HOTSEARCH_BACKUP]:
            try:
                resp = cffi_requests.get(
                    api_url,
                    impersonate="chrome",
                    timeout=15,
                    proxies=proxy_dict,
                    headers={
                        "Referer": "https://www.douyin.com/",
                        "Origin": "https://www.douyin.com",
                    },
                )
                if resp.status_code != 200:
                    continue

                data = resp.json()
                word_list = (
                    data.get("data", {}).get("word_list")
                    or data.get("word_list")
                    or data.get("data", {}).get("list")
                    or []
                )

                if not word_list:
                    continue

                items = []
                for rank, word_data in enumerate(
                    word_list[:self.max_per_platform], 1
                ):
                    word = (
                        word_data.get("word")
                        or word_data.get("keyword")
                        or ""
                    )
                    if not word:
                        continue

                    word = safe_str(word, max_len=200)
                    hot_value = (
                        word_data.get("hot_value", 0)
                        or word_data.get("score", 0)
                        or 0
                    )
                    search_url = f"https://www.douyin.com/search/{quote(word)}"

                    items.append({
                        "title": word,
                        "url": search_url,
                        "description": f"热度: {self._fmt_num(hot_value)} | 排名: #{rank}",
                        "tags": ["抖音", "短视频", "热搜"],
                        "extra": {
                            "platform": "douyin",
                            "video_url": search_url,
                            "author": "",
                            "views": hot_value,
                            "likes": 0,
                            "favorites": 0,
                            "comments": 0,
                            "duration": 0,
                            "rank": rank,
                            "hot_value": hot_value,
                            "type": "hot_search",
                        },
                    })

                if items:
                    print(f"  [抖音/cffi] 获取 {len(items)} 条热搜词")
                    return items

            except Exception as e:
                print(f"  [抖音/cffi] 失败 ({api_url}): {e}")
                continue

        return []

    # ════════════════════════════════════════════════════════════
    #  快手热门
    # ════════════════════════════════════════════════════════════

    def _fetch_kuaishou(self) -> list[dict]:
        """快手热门：通过 GraphQL 接口获取热门视频（requests → curl_cffi）"""
        # 尝试标准 requests
        items = self._fetch_kuaishou_graphql()
        if items:
            return items

        # 备选：curl_cffi
        if HAS_CFFI:
            print("  [快手] 尝试 curl_cffi...")
            items = self._fetch_kuaishou_cffi()
            if items:
                return items

        print("  [快手] 所有方案均失败，跳过")
        return []

    def _fetch_kuaishou_graphql(self) -> list[dict]:
        """快手 GraphQL 热门视频接口"""
        # 快手热门视频 GraphQL 查询
        graphql_query = """
        query visionHotRank($page: String, $pageSize: Int) {
          visionHotRank(page: $page, pageSize: $pageSize) {
            visionHotRank {
              photoId
              caption
              coverUrl
              duration
              viewCount
              likeCount
              commentCount
              author {
                name
                id
              }
            }
          }
        }
        """.strip()

        payload = {
            "operationName": "visionHotRank",
            "variables": {
                "page": "1",
                "pageSize": self.max_per_platform,
            },
            "query": graphql_query,
        }

        headers = {
            "Content-Type": "application/json",
            "Referer": "https://www.kuaishou.com/",
            "Origin": "https://www.kuaishou.com",
        }

        try:
            resp = self.session.post(
                self.KUAISHOU_GRAPHQL,
                json=payload,
                headers=headers,
                timeout=15,
            )

            if resp.status_code != 200:
                print(f"  [快手] HTTP {resp.status_code}")
                return []

            data = resp.json()
            # 解析 GraphQL 返回（兼容嵌套结构）
            rank_data = data.get("data", {}).get("visionHotRank", {})
            if isinstance(rank_data, dict):
                rank_data = rank_data.get("visionHotRank", [])

            if not rank_data:
                print("  [快手] 未获取到热门视频数据")
                return []

            items = []
            for rank, video in enumerate(
                rank_data[:self.max_per_platform], 1
            ):
                photo_id = video.get("photoId", "")
                caption = safe_str(
                    video.get("caption", ""), max_len=200
                )
                if not caption:
                    caption = f"快手热门视频 #{rank}"

                video_url = (
                    f"https://www.kuaishou.com/short-video/{photo_id}"
                    if photo_id else ""
                )
                author = video.get("author", {})
                author_name = safe_str(
                    author.get("name", ""), max_len=100
                )

                views = video.get("viewCount", 0)
                likes = video.get("likeCount", 0)
                comments = video.get("commentCount", 0)
                duration = video.get("duration", 0)

                desc = (f"作者: {author_name} | "
                        f"播放: {self._fmt_num(views)} | "
                        f"点赞: {self._fmt_num(likes)}")

                items.append({
                    "title": caption,
                    "url": video_url or "https://www.kuaishou.com/",
                    "description": desc,
                    "tags": ["快手", "短视频", "热门"],
                    "extra": {
                        "platform": "kuaishou",
                        "video_url": video_url,
                        "author": author_name,
                        "views": views,
                        "likes": likes,
                        "favorites": 0,
                        "comments": comments,
                        "duration": duration,
                        "rank": rank,
                        "photo_id": photo_id,
                    },
                })

            print(f"  [快手] 获取 {len(items)} 条热门视频")
            return items

        except Exception as e:
            print(f"  [快手] GraphQL 请求失败: {e}")
            logger.exception("[快手] 抓取异常")
            return []

    def _fetch_kuaishou_cffi(self) -> list[dict]:
        """使用 curl_cffi 抓取快手热门（备选方案）"""
        proxy_dict = {"http": self.proxy, "https": self.proxy} if self.proxy else None

        graphql_query = """
        query visionHotRank($page: String, $pageSize: Int) {
          visionHotRank(page: $page, pageSize: $pageSize) {
            visionHotRank {
              photoId
              caption
              coverUrl
              duration
              viewCount
              likeCount
              commentCount
              author { name id }
            }
          }
        }
        """.strip()

        payload = {
            "operationName": "visionHotRank",
            "variables": {
                "page": "1",
                "pageSize": self.max_per_platform,
            },
            "query": graphql_query,
        }

        try:
            resp = cffi_requests.post(
                self.KUAISHOU_GRAPHQL,
                json=payload,
                impersonate="chrome",
                timeout=15,
                proxies=proxy_dict,
                headers={
                    "Content-Type": "application/json",
                    "Referer": "https://www.kuaishou.com/",
                    "Origin": "https://www.kuaishou.com",
                },
            )

            if resp.status_code != 200:
                print(f"  [快手/cffi] HTTP {resp.status_code}")
                return []

            data = resp.json()
            rank_data = data.get("data", {}).get("visionHotRank", {})
            if isinstance(rank_data, dict):
                rank_data = rank_data.get("visionHotRank", [])

            if not rank_data:
                print("  [快手/cffi] 未获取到数据")
                return []

            items = []
            for rank, video in enumerate(
                rank_data[:self.max_per_platform], 1
            ):
                photo_id = video.get("photoId", "")
                caption = safe_str(
                    video.get("caption", ""), max_len=200
                ) or f"快手热门 #{rank}"
                video_url = (
                    f"https://www.kuaishou.com/short-video/{photo_id}"
                    if photo_id else ""
                )
                author_name = safe_str(
                    video.get("author", {}).get("name", ""), max_len=100
                )

                items.append({
                    "title": caption,
                    "url": video_url or "https://www.kuaishou.com/",
                    "description": (f"作者: {author_name} | "
                                    f"播放: {self._fmt_num(video.get('viewCount', 0))}"),
                    "tags": ["快手", "短视频", "热门"],
                    "extra": {
                        "platform": "kuaishou",
                        "video_url": video_url,
                        "author": author_name,
                        "views": video.get("viewCount", 0),
                        "likes": video.get("likeCount", 0),
                        "favorites": 0,
                        "comments": video.get("commentCount", 0),
                        "duration": video.get("duration", 0),
                        "rank": rank,
                        "photo_id": photo_id,
                    },
                })

            print(f"  [快手/cffi] 获取 {len(items)} 条")
            return items

        except Exception as e:
            print(f"  [快手/cffi] 备选方案失败: {e}")
            logger.exception("[快手/cffi] 抓取异常")
            return []

    # ════════════════════════════════════════════════════════════
    #  小红书
    # ════════════════════════════════════════════════════════════

    def _fetch_xiaohongshu(self) -> list[dict]:
        """小红书：尝试公开页面数据，失败则跳过

        小红书没有稳定的公开 API，这里尝试从探索页 HTML 中
        提取 __INITIAL_STATE__ 初始数据。
        """
        try:
            resp = self._get(self.XHS_EXPLORE, timeout=15)
            if resp.status_code != 200:
                print(f"  [小红书] HTTP {resp.status_code}，跳过")
                return []

            text = resp.text
            # 小红书页面包含 __INITIAL_STATE__ 数据
            match = re.search(
                r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>',
                text,
                re.DOTALL,
            )
            if not match:
                print("  [小红书] 无法解析页面数据，跳过")
                return []

            # 解析 JSON（可能包含 undefined 需要替换为 null）
            raw_json = match.group(1)
            raw_json = raw_json.replace("undefined", "null")
            state = json.loads(raw_json)

            # 提取热门笔记（兼容多种数据路径）
            feeds = (
                state.get("homeFeed", {}).get("feeds", [])
                or state.get("explore", {}).get("feeds", [])
                or state.get("feed", {}).get("feeds", [])
                or []
            )

            if not feeds:
                print("  [小红书] 未找到热门笔记数据，跳过")
                return []

            items = []
            for rank, feed in enumerate(feeds[:self.max_per_platform], 1):
                if not isinstance(feed, dict):
                    continue
                note = feed.get("noteCard", feed)
                note_id = note.get("noteId", "") or feed.get("id", "")
                title = safe_str(
                    note.get("title", "") or note.get("desc", ""),
                    max_len=200,
                )
                if not title:
                    title = f"小红书热门笔记 #{rank}"

                user = note.get("user", {})
                author = safe_str(
                    user.get("nickname", "") or user.get("name", ""),
                    max_len=100,
                )

                interact = note.get("interactInfo", {})
                views = self._parse_num(interact.get("viewCount", "0"))
                likes = self._parse_num(interact.get("likedCount", "0"))
                comments = self._parse_num(interact.get("commentCount", "0"))
                favorites = self._parse_num(interact.get("collectedCount", "0"))

                note_url = (
                    f"https://www.xiaohongshu.com/explore/{note_id}"
                    if note_id else "https://www.xiaohongshu.com/"
                )

                items.append({
                    "title": title,
                    "url": note_url,
                    "description": (f"作者: {author} | "
                                    f"点赞: {self._fmt_num(likes)} | "
                                    f"收藏: {self._fmt_num(favorites)}"),
                    "tags": ["小红书", "短视频", "热门"],
                    "extra": {
                        "platform": "xiaohongshu",
                        "video_url": note_url,
                        "author": author,
                        "views": views,
                        "likes": likes,
                        "favorites": favorites,
                        "comments": comments,
                        "duration": 0,
                        "rank": rank,
                        "note_id": note_id,
                    },
                })

            print(f"  [小红书] 获取 {len(items)} 条热门笔记")
            return items

        except Exception as e:
            print(f"  [小红书] 抓取失败，跳过: {e}")
            logger.exception("[小红书] 抓取异常")
            return []

    # ════════════════════════════════════════════════════════════
    #  工具方法
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def _fmt_num(n) -> str:
        """格式化数字显示（万、亿）"""
        try:
            n = int(n)
        except (ValueError, TypeError):
            return "0"
        if n >= 100_000_000:
            return f"{n / 100_000_000:.1f}亿"
        elif n >= 10_000:
            return f"{n / 10_000:.1f}万"
        return str(n)

    @staticmethod
    def _parse_num(s) -> int:
        """解析可能包含中文单位的数字字符串"""
        if isinstance(s, (int, float)):
            return int(s)
        if not s:
            return 0
        s = str(s).strip()
        try:
            if "亿" in s:
                return int(float(s.replace("亿", "")) * 100_000_000)
            elif "万" in s:
                return int(float(s.replace("万", "")) * 10_000)
            return int(s)
        except (ValueError, TypeError):
            return 0
