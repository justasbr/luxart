"""One adaptive request budget shared by every download worker."""
from email.utils import parsedate_to_datetime
import math
import threading
import time

class AdaptiveRate:
    def __init__(self, start_rate=10, max_rate=40, *, clock=time.monotonic,
                 sleep=time.sleep, wall_clock=time.time, log=None):
        if not (math.isfinite(start_rate) and math.isfinite(max_rate) and 0 < start_rate <= max_rate):
            raise ValueError('Rates must be finite and 0 < start-rate <= max-rate')
        self.rate, self.max_rate = start_rate, max_rate
        self.clock, self.sleep, self.wall_clock = clock, sleep, wall_clock
        self.log = log or (lambda message: print(message, flush=True))
        self.lock = threading.Lock()
        self.last_start = None
        self.pause_until = 0
        self.last_change = clock()
        self.successes = 0
        self.epoch = 0

    def acquire(self):
        # Recheck after sleeping: other workers may have lowered the rate or paused.
        while True:
            with self.lock:
                now = self.clock()
                next_start = now if self.last_start is None else self.last_start + 1/self.rate
                delay = max(next_start, self.pause_until) - now
                if delay <= 0:
                    self.last_start = now
                    return self.epoch
            self.sleep(delay)

    def success(self, epoch):
        with self.lock:
            now = self.clock()
            if epoch != self.epoch or now < self.pause_until:
                return
            self.successes += 1
            if self.successes >= 50 and now-self.last_change >= 30 and self.rate < self.max_rate:
                self.rate = min(self.max_rate, self.rate*1.1)
                self.successes = 0
                self.last_change = now
                self.log(f'Rate ↑ {self.rate:.2f} req/sec after sustained successful responses')

    def failure(self, status, retry_after=None):
        delay = 30 if status in {403,429} else 5
        if retry_after:
            try:
                retry_seconds = float(retry_after)
            except (ValueError, TypeError):
                try:
                    retry_seconds = parsedate_to_datetime(retry_after).timestamp()-self.wall_clock()
                except (ValueError, TypeError, OverflowError):
                    retry_seconds = 0
            if math.isfinite(retry_seconds):
                delay = max(delay, retry_seconds)
        with self.lock:
            now = self.clock()
            # A wave of in-flight failures triggers one reduction, not one per worker.
            if now >= self.pause_until:
                self.rate = max(0.5, self.rate/2)
                self.epoch += 1
                self.log(f'Rate ↓ {self.rate:.2f} req/sec; HTTP {status or "network error"}; cooling down {delay:g}s')
            self.pause_until = max(self.pause_until, now+delay)
            self.last_change = self.pause_until
            self.successes = 0
