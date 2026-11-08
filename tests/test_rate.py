import unittest
from rate import AdaptiveRate

class Clock:
    def __init__(self): self.now=0
    def time(self): return self.now
    def sleep(self, seconds): self.now+=seconds

class RateTests(unittest.TestCase):
    def make(self, **kwargs):
        self.clock=Clock()
        return AdaptiveRate(clock=self.clock.time,sleep=self.clock.sleep,log=lambda _:None,**kwargs)
    def test_requests_are_spaced_globally(self):
        r=self.make();r.acquire();r.acquire();r.acquire()
        self.assertAlmostEqual(self.clock.now,0.2)
    def test_increase_requires_time_and_successes_and_stays_capped(self):
        r=self.make(max_rate=11)
        for _ in range(100):r.success(0)
        self.assertEqual(r.rate,10)
        self.clock.now=31;r.success(0)
        self.assertEqual(r.rate,11)
        self.clock.now=62
        for _ in range(100):r.success(0)
        self.assertEqual(r.rate,11)
    def test_block_halves_rate_and_pauses_all_workers(self):
        r=self.make();r.failure(429,'45')
        self.assertEqual(r.rate,5)
        r.acquire();self.assertGreaterEqual(self.clock.now,45)
    def test_inflight_block_wave_does_not_repeatedly_halve(self):
        r=self.make();r.failure(403)
        for _ in range(31):r.failure(403)
        self.assertEqual(r.rate,5)
    def test_stale_successes_cannot_raise_rate_after_failure(self):
        r=self.make();old=r.acquire();r.failure(429)
        self.clock.now=100
        for _ in range(100):r.success(old)
        self.assertEqual(r.rate,5)
    def test_retry_after_date(self):
        r=self.make(wall_clock=lambda:0)
        r.failure(429,'Thu, 01 Jan 1970 00:02:00 GMT')
        r.acquire();self.assertEqual(self.clock.now,120)
    def test_network_failure_slows_down_and_recovers(self):
        r=self.make();r.failure(None)
        self.assertEqual(r.rate,5)
        epoch=r.acquire();self.clock.now+=31
        for _ in range(50):r.success(epoch)
        self.assertEqual(r.rate,5.5)
