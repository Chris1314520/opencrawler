#!/usr/bin/env python3
"""统一事件监视器 —— 周期性抓取 + 存储 + 通知"""

import argparse
import os
import sys
import time
import yaml
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

sys.path.insert(0, os.path.dirname(__file__))
from storage import Store
from notifier import Notifier
from fetchers.github_trending import GitHubTrendingFetcher
from fetchers.hackernews import HackerNewsFetcher
from fetchers.rss_feeds import RSSFetcherWithProxy
from fetchers.curl_cffi_rss import CurlCffiRSSFetcher
from fetchers.nvd_cve import NVDCVEFetcher
from fetchers.shortvideo_trending import ShortVideoTrendingFetcher

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Monitor:
    def __init__(self, config: dict):
        self.cfg = config
        self.proxy = config.get("proxy", "")
        self.store = Store(retention_days=config.get("retention_days", 30))
        self.notifier = Notifier()
        self.intervals = config.get("intervals", {})

        # 初始化抓取器
        self.fetchers = {}
        self._init_fetchers()

    def _init_fetchers(self):
        # GitHub Trending
        if self.cfg.get("github_trending", {}).get("enabled", True):
            self.fetchers["github_trending"] = GitHubTrendingFetcher(
                proxy=self.proxy,
                languages=self.cfg["github_trending"].get("languages", [""]),
                since=self.cfg["github_trending"].get("since", ["daily"]),
                spoken_language=self.cfg["github_trending"].get("spoken_language", ""),
            )

        # Hacker News
        if self.cfg.get("hackernews", {}).get("enabled", True):
            self.fetchers["hackernews"] = HackerNewsFetcher(
                proxy=self.proxy,
                max_items=self.cfg["hackernews"].get("max_items", 30),
            )

        # RSS Feeds (标准 requests)
        rss_feeds = self.cfg.get("rss_feeds", [])
        if rss_feeds:
            self.fetchers["rss"] = RSSFetcherWithProxy(
                proxy=self.proxy,
                feeds=rss_feeds,
            )

        # curl_cffi RSS (绕过 TLS 指纹检测)
        cffi_feeds = self.cfg.get("curl_cffi_feeds", [])
        if cffi_feeds:
            self.fetchers["curl_cffi_rss"] = CurlCffiRSSFetcher(
                proxy=self.proxy,
                feeds=cffi_feeds,
            )

        # NVD CVE 漏洞
        if self.cfg.get("nvd_cve", {}).get("enabled", True):
            self.fetchers["nvd_cve"] = NVDCVEFetcher(
                proxy=self.proxy,
                days_back=self.cfg["nvd_cve"].get("days_back", 7),
                max_results=self.cfg["nvd_cve"].get("max_results", 20),
            )

        # 短视频热门（B站/抖音/快手/小红书）
        if self.cfg.get("shortvideo_trending", {}).get("enabled", True):
            self.fetchers["shortvideo_trending"] = ShortVideoTrendingFetcher(
                proxy=self.proxy,
                max_per_platform=self.cfg["shortvideo_trending"].get("max_per_platform", 20),
            )

    def run_once(self):
        """执行一轮抓取"""
        print(f"\n{'─'*40}\n  [{datetime.now().strftime('%H:%M:%S')}] 开始一轮抓取\n{'─'*40}")
        total_new = 0
        for source_name, fetcher in self.fetchers.items():
            print(f"\n  [{source_name}] 抓取中...")
            try:
                items = fetcher.fetch()
                new_count = 0
                for item in items:
                    is_new = self.store.upsert(
                        source=source_name,
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        description=item.get("description", ""),
                        tags=item.get("tags", []),
                        extra=item.get("extra", {}),
                    )
                    if is_new:
                        new_count += 1
                print(f"  [{source_name}] 获取 {len(items)} 条，新增 {new_count} 条")
                total_new += new_count
            except Exception as e:
                print(f"  [{source_name}] 错误: {e}")

        if total_new > 0:
            self.notifier.send(
                title=f"监视器 - {total_new} 条新内容",
                body=f"本轮共发现 {total_new} 条新条目",
                items=[f"[{source_name}] {total_new} 条" for source_name in self.fetchers],
            )

        # 清理过期数据
        self.store.cleanup_old()
        print(f"\n  [完成] 新增 {total_new} 条, 总计 {self.store.stats()['total']} 条")

    def start_scheduler(self):
        """启动定时调度"""
        scheduler = BackgroundScheduler()
        for source_name, fetcher in self.fetchers.items():
            minutes = self.intervals.get(source_name, 60)
            scheduler.add_job(
                func=self._job_wrapper,
                trigger=IntervalTrigger(minutes=minutes),
                args=[source_name, fetcher],
                id=source_name,
                name=source_name,
                replace_existing=True,
            )
            print(f"  [{source_name}] 每 {minutes} 分钟抓取一次")

        scheduler.start()
        print(f"\n  调度器已启动，共 {len(self.fetchers)} 个任务\n")

        # 立即执行一轮
        self.run_once()

        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n  正在停止...")
            scheduler.shutdown()
            self.store.close()
            print("  已停止")

    def _job_wrapper(self, source_name: str, fetcher):
        """定时任务包装器"""
        print(f"\n  [{source_name}] 定时任务触发 ({datetime.now().strftime('%H:%M:%S')})")
        try:
            items = fetcher.fetch()
            new_count = 0
            for item in items:
                is_new = self.store.upsert(
                    source=source_name,
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                    tags=item.get("tags", []),
                    extra=item.get("extra", {}),
                )
                if is_new:
                    new_count += 1
            print(f"  [{source_name}] 获取 {len(items)} 条，新增 {new_count} 条")
            if new_count > 10:
                self.notifier.send(
                    title=f"[{source_name}] {new_count} 条新内容",
                    items=[item.get("title","") for item in items[:5]],
                )
        except Exception as e:
            print(f"  [{source_name}] 定时任务错误: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="统一事件监视器")
    parser.add_argument("--once", action="store_true", help="只运行一轮后退出")
    parser.add_argument("--config", default=CONFIG_PATH, help="配置文件路径")
    args = parser.parse_args()

    config = load_config()
    monitor = Monitor(config)

    if args.once:
        monitor.run_once()
        monitor.store.close()
        print("  单次运行完成")
    else:
        monitor.start_scheduler()
