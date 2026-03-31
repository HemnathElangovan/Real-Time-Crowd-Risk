# logger.py — CSV logger + in-memory history
import csv, os, time
from datetime import datetime
import config

class Logger:
    HISTORY_MAX = 120

    def __init__(self):
        os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
        self._last_log = 0
        self._history  = []
        if not os.path.exists(config.LOG_FILE):
            with open(config.LOG_FILE, "w", newline="") as f:
                csv.writer(f).writerow(["timestamp", "count", "risk"])

    def record(self, count: int, risk: str):
        now = time.time()
        if now - self._last_log < config.LOG_INTERVAL_SECONDS:
            return
        self._last_log = now
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(config.LOG_FILE, "a", newline="") as f:
            csv.writer(f).writerow([ts, count, risk])
        self._history.append({"time": ts, "count": count, "risk": risk})
        if len(self._history) > self.HISTORY_MAX:
            self._history.pop(0)

    @property
    def history(self):
        return self._history

    @property
    def recent_counts(self):
        return [h["count"] for h in self._history[-60:]]
