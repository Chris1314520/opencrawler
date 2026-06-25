"""GitHub Trending 抓取器 —— 通过 RSSHub 或直接解析"""

import logging
import re
from bs4 import BeautifulSoup
from . import BaseFetcher, safe_str

logger = logging.getLogger(__name__)


class GitHubTrendingFetcher(BaseFetcher):
    BASE = "https://github.com/trending"

    def __init__(self, proxy: str = "", languages: list = None,
                 since: list = None, spoken_language: str = ""):
        super().__init__(proxy)
        self.languages = languages or [""]
        self.since_list = since or ["daily"]
        self.spoken = spoken_language

    def fetch(self) -> list[dict]:
        results = []
        for lang in self.languages:
            for since in self.since_list:
                try:
                    items = self._fetch_one(lang, since)
                    results.extend(items)
                except Exception as e:
                    logger.warning("[GitHub] 抓取失败 (lang=%r, since=%s): %s",
                                   lang, since, e)
        return results

    def _fetch_one(self, language: str, since: str) -> list[dict]:
        url = f"{self.BASE}/{language}?since={since}"
        if self.spoken:
            url += f"&spoken_language_code={self.spoken}"

        try:
            resp = self._get(url, timeout=30)
        except Exception as e:
            logger.warning("[GitHub] 请求失败: %s", e)
            return []

        if resp.status_code != 200:
            logger.warning("[GitHub] HTTP %d for %s", resp.status_code, url)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for article in soup.select("article.Box-row"):
            h2 = article.select_one("h2 a")
            if not h2:
                continue
            href = h2.get("href", "").strip()
            full_name = href.strip("/")
            # repo name: "owner/repo"
            parts = full_name.split("/")
            if len(parts) < 2:
                continue
            author, repo = parts[0], parts[1]

            title = full_name
            desc_el = article.select_one("p")
            description = safe_str(desc_el.text) if desc_el else ""

            stars_el = article.select_one(".d-inline-block.float-sm-right")
            stars_text = stars_el.text.strip() if stars_el else ""
            stars = self._parse_stars(stars_text)

            lang_el = article.select_one("[itemprop=programmingLanguage]")
            plang = lang_el.text.strip() if lang_el else ""

            items.append({
                "title": title,
                "url": f"https://github.com/{full_name}",
                "description": description,
                "tags": ["GitHub", "trending", since] + ([plang] if plang else []),
                "extra": {
                    "stars_today": stars,
                    "author": author,
                    "repo": repo,
                    "language": plang,
                    "trending_since": since,
                },
            })
        return items

    @staticmethod
    def _parse_stars(text: str) -> int:
        nums = re.findall(r'[\d,]+', text)
        if nums:
            return int(nums[0].replace(",", ""))
        return 0
