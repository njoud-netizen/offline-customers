"""قاعدة بيانات SQLite بسيطة لمنع إعادة معالجة نفس (رقم الجوال + Sales Order ID) بين التشغيلات."""
import sqlite3
from datetime import datetime
from pathlib import Path


class DedupStore:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS processed (
                phone_key TEXT NOT NULL,
                sales_order_id TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                PRIMARY KEY (phone_key, sales_order_id)
            )
        """)
        self.conn.commit()

    def is_processed(self, phone_key: str, sales_order_id: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM processed WHERE phone_key = ? AND sales_order_id = ?",
            (phone_key, sales_order_id),
        )
        return cur.fetchone() is not None

    def mark_processed(self, phone_key: str, sales_order_id: str):
        self.conn.execute(
            "INSERT OR IGNORE INTO processed (phone_key, sales_order_id, processed_at) VALUES (?, ?, ?)",
            (phone_key, sales_order_id, datetime.now().isoformat(timespec="seconds")),
        )

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
