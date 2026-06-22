"""通知模块 —— 控制台输出 + 可扩展桌面/Webhook 通知"""

import json
import os
from datetime import datetime

NOTIFY_LOG = os.path.join(os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data")), "notifications.json")


class Notifier:
    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url
        self._session = None

    def send(self, title: str, body: str = "", items: list = None):
        """发送通知"""
        now = datetime.now().strftime("%m-%d %H:%M:%S")
        print(f"\n{'='*50}")
        print(f"  [{now}] {title}")
        if body:
            print(f"  {body}")
        if items:
            for item in items[:10]:
                print(f"  - {item}")
            if len(items) > 10:
                print(f"  ... 还有 {len(items) - 10} 条")
        print(f"{'='*50}\n")

        if self.webhook_url:
            self._send_webhook(title, body, items)

        self._log(title, body, items)

    def _send_webhook(self, title: str, body: str, items: list):
        try:
            import requests
            if not self._session:
                self._session = requests.Session()
            payload = {
                "title": title,
                "body": body,
                "items": items[:20] if items else [],
            }
            self._session.post(self.webhook_url, json=payload, timeout=10)
        except Exception as e:
            print(f"  [通知] Webhook 失败: {e}")

    @staticmethod
    def _log(title: str, body: str, items: list):
        try:
            os.makedirs(os.path.dirname(NOTIFY_LOG), exist_ok=True)
            existing = []
            if os.path.exists(NOTIFY_LOG):
                with open(NOTIFY_LOG, "r", encoding="utf-8") as f:
                    try:
                        existing = json.load(f)
                    except json.JSONDecodeError:
                        existing = []
            existing.append({
                "time": datetime.now().isoformat(),
                "title": title,
                "body": body,
                "item_count": len(items) if items else 0,
            })
            # 只保留最近 200 条
            existing = existing[-200:]
            with open(NOTIFY_LOG, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
