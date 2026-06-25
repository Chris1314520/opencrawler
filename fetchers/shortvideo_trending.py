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

优化要点：
  - 使用基类 _fetch_with_fallback / _post_with_fallback 统一 requests → curl_cffi 降级
  - 每个平台解析逻辑只写一份（parser_fn），消除 _xxx_cffi 重复方法
  - 全部使用 logger 替代 print
"""

import json
import logging
import re
from urllib.parse import quote

from . import BaseFetcher, safe_str

logger = logging.getLogger(__name__)


class ShortVideoTrendingFetcher(BaseFetcher):
    """短视频平台热门内容聚合抓取器

    继承 BaseFetcher，使用 requests.Session 发起请求；
    遇到 TLS 指纹检测 / 反爬时，通过 _fetch_with_fallback 自动降级到 curl_cffi。
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
        logger.info("[短视频/B站] 抓取中...")
        results.extend(self._fetch_bilibili())

        # 2. 抖音热搜
        logger.info("[短视频/抖音] 抓取中...")
        results.extend(self._fetch_douyin())

        # 3. 快手热门
        logger.info("[短视频/快手] 抓取中...")
        results.extend(self._fetch_kuaishou())

        # 4. 小红书（尝试公开页面数据，失败则跳过）
        logger.info("[短视频/小红书] 抓取中...")
        results.extend(self._fetch_xiaohongshu())

        # 5. 视频号（无公开 API，跳过）
        logger.info("[短视频/视频号] 无公开 API，跳过")

        logger.info("[短视频] 共获取 %d 条", len(results))
        return results

    # ════════════════════════════════════════════════════════════
    #  B站（Bilibili）—— 公开热门视频 API
    # ════════════════════════════════════════════════════════════

    def _fetch_bilibili(self) -> list[dict]:
        """B站热门视频：通过公开 API 获取真实 BV 号视频链接。

        使用 _fetch_with_fallback 自动降级到 curl_cffi。
        """
        url = f"{self.BILIBILI_POPULAR}?ps={self.max_per_platform}&pn=1"
        headers = {
            "Referer": "https://www.bilibili.com/",
            "Origin": "https://www.bilibili.com",
        }
        return self._fetch_with_fallback(
            url, self._parse_bilibili, timeout=15, headers=headers
        )

    def _parse_bilibili(self, data, resp) -> list[dict] | None:
        """解析 B站 API 响应。

        返回 None 触发 curl_cffi 降级（API 错误时），
        返回 [] 表示合法无数据，返回 list 表示成功。
        """
        if data.get("code") != 0:
            logger.warning("[B站] API 返回错误: code=%s, msg=%s",
                           data.get("code"), data.get("message"))
            return None  # 触发降级

        video_list = data.get("data", {}).get("list", [])
        if not video_list:
            logger.info("[B站] 未获取到视频列表")
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
            cover_url = video.get("pic", "")  # 封面图

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
                    "cover_url": cover_url,
                },
            })

        logger.info("[B站] 获取 %d 条热门视频", len(items))
        return items

    # ════════════════════════════════════════════════════════════
    #  抖音热搜
    # ════════════════════════════════════════════════════════════

    def _fetch_douyin(self) -> list[dict]:
        """抖音热搜：获取热搜词和热度值。

        依次尝试主 API → 备选 API，每个 API 各自带有 curl_cffi 降级。
        """
        headers = {
            "Referer": "https://www.douyin.com/",
            "Origin": "https://www.douyin.com",
        }

        # 尝试主 API
        items = self._fetch_with_fallback(
            self.DOUYIN_HOTSEARCH, self._parse_douyin,
            timeout=15, headers=headers
        )
        if items:
            return items

        # 尝试备选 API
        logger.info("[抖音] 主 API 失败，尝试备选 API...")
        items = self._fetch_with_fallback(
            self.DOUYIN_HOTSEARCH_BACKUP, self._parse_douyin,
            timeout=15, headers=headers
        )
        if items:
            return items

        logger.warning("[抖音] 所有方案均失败")
        return []

    def _parse_douyin(self, data, resp) -> list[dict] | None:
        """解析抖音热搜 API 响应。

        兼容多种返回结构。返回 None 触发降级（无数据时可能为反爬）。
        """
        # 不同 API 返回结构可能不同，兼容多种格式
        word_list = (
            data.get("data", {}).get("word_list")
            or data.get("word_list")
            or data.get("data", {}).get("list")
            or []
        )

        if not word_list:
            return None  # 触发降级

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

        logger.info("[抖音] 获取 %d 条热搜词", len(items))
        return items

    # ════════════════════════════════════════════════════════════
    #  快手热门
    # ════════════════════════════════════════════════════════════

    def _fetch_kuaishou(self) -> list[dict]:
        """快手热门：通过 GraphQL 接口获取热门视频。

        使用 _post_with_fallback 自动降级到 curl_cffi。
        """
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

        return self._post_with_fallback(
            self.KUAISHOU_GRAPHQL, self._parse_kuaishou,
            timeout=15, json=payload, headers=headers
        )

    def _parse_kuaishou(self, data, resp) -> list[dict] | None:
        """解析快手 GraphQL 响应。

        返回 None 触发降级（无数据时可能为反爬）。
        """
        # 解析 GraphQL 返回（兼容嵌套结构）
        rank_data = data.get("data", {}).get("visionHotRank", {})
        if isinstance(rank_data, dict):
            rank_data = rank_data.get("visionHotRank", [])

        if not rank_data:
            return None  # 触发降级

        items = []
        for rank, video in enumerate(rank_data[:self.max_per_platform], 1):
            photo_id = video.get("photoId", "")
            caption = safe_str(video.get("caption", ""), max_len=200)
            if not caption:
                caption = f"快手热门视频 #{rank}"

            video_url = (
                f"https://www.kuaishou.com/short-video/{photo_id}"
                if photo_id else ""
            )
            author = video.get("author", {})
            author_name = safe_str(author.get("name", ""), max_len=100)

            views = video.get("viewCount", 0)
            likes = video.get("likeCount", 0)
            comments = video.get("commentCount", 0)
            duration = video.get("duration", 0)
            cover_url = video.get("coverUrl", "") or video.get("photoUrl", "")

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
                    "cover_url": cover_url,
                },
            })

        logger.info("[快手] 获取 %d 条热门视频", len(items))
        return items

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
                logger.warning("[小红书] HTTP %d，跳过", resp.status_code)
                return []

            text = resp.text
            # 小红书页面包含 __INITIAL_STATE__ 数据
            match = re.search(
                r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>',
                text,
                re.DOTALL,
            )
            if not match:
                logger.info("[小红书] 无法解析页面数据，跳过")
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
                logger.info("[小红书] 未找到热门笔记数据，跳过")
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

                # 封面图：优先 imageList 第一张，其次 cover.url
                cover_url = ""
                image_list = note.get("imageList", [])
                if image_list and isinstance(image_list, list):
                    first_img = image_list[0]
                    if isinstance(first_img, dict):
                        cover_url = first_img.get("urlDefault", "") or first_img.get("url", "")
                    elif isinstance(first_img, str):
                        cover_url = first_img
                if not cover_url:
                    cover = note.get("cover", {})
                    if isinstance(cover, dict):
                        cover_url = cover.get("urlDefault", "") or cover.get("url", "")

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
                        "cover_url": cover_url,
                    },
                })

            logger.info("[小红书] 获取 %d 条热门笔记", len(items))
            return items

        except Exception as e:
            logger.warning("[小红书] 抓取失败，跳过: %s", e, exc_info=True)
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
