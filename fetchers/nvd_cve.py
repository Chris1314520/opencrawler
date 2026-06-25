"""NVD CVE 漏洞抓取器 —— 通过 NIST NVD API 2.0（直连，不走代理）"""

import logging
from datetime import datetime, timedelta, timezone

from . import BaseFetcher

logger = logging.getLogger(__name__)


class NVDCVEFetcher(BaseFetcher):
    """从 NVD API 获取近期 CVE 漏洞。

    继承 BaseFetcher，复用自动重试 / 连接池 / 统一日志。
    NVD 是美国政府站点，直连即可（trust_env=False 已在基类设置）。
    """

    API = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def __init__(self, proxy: str = "", days_back: int = 7, max_results: int = 20):
        # NVD 直连，不使用代理
        super().__init__(proxy="", timeout=30)
        self.days_back = days_back
        self.max_results = max_results

    def fetch(self) -> list[dict]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=self.days_back)
        params = {
            "pubStartDate": start.strftime("%Y-%m-%dT00:00:00.000"),
            "pubEndDate": end.strftime("%Y-%m-%dT23:59:59.999"),
            "resultsPerPage": min(self.max_results, 50),
        }

        try:
            resp = self._get(self.API, timeout=30, params=params)
            if resp.status_code != 200:
                logger.warning("[CVE] HTTP %d", resp.status_code)
                return []
            data = resp.json()
        except Exception as e:
            logger.error("[CVE] 请求失败: %s", e)
            return []

        results = []
        for vuln in data.get("vulnerabilities", []):
            cve = vuln.get("cve", {})
            cve_id = cve.get("id", "")
            desc = self._get_desc(cve)
            url = f"https://nvd.nist.gov/vuln/detail/{cve_id}"

            metrics = cve.get("metrics", {})
            cvss_v3 = metrics.get("cvssMetricV31", []) or metrics.get("cvssMetricV30", [])
            score = ""
            if cvss_v3:
                score = str(cvss_v3[0].get("cvssData", {}).get("baseScore", ""))
                severity = cvss_v3[0].get("cvssData", {}).get("baseSeverity", "")
                if severity:
                    score += f" ({severity})"

            tags = ["安全", "CVE"]
            if score:
                try:
                    s = float(score.split(" ")[0])
                    if s >= 9.0:
                        tags.append("严重")
                    elif s >= 7.0:
                        tags.append("高危")
                except ValueError:
                    pass

            results.append({
                "title": f"{cve_id}: {desc[:120]}",
                "url": url,
                "description": desc,
                "tags": tags,
                "extra": {
                    "cve_id": cve_id,
                    "cvss": score,
                    "published": cve.get("published", ""),
                },
            })
        return results

    @staticmethod
    def _get_desc(cve: dict) -> str:
        for d in cve.get("descriptions", []):
            if d.get("lang") == "en":
                return d.get("value", "")
        if cve.get("descriptions"):
            return cve["descriptions"][0].get("value", "")
        return ""
