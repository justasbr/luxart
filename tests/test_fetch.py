import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
import importer
from rate import AdaptiveRate

class Response:
    def __init__(self, body): self.body=body
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self): return self.body.encode()

class FetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.now=0
        def sleep(s):self.now+=s
        self.rate=AdaptiveRate(clock=lambda:self.now,sleep=sleep,log=lambda _:None)
        for target,value in [('CACHE',Path(self.tmp.name)),('robots',None),('limiter',self.rate)]:
            p=patch.object(importer,target,value,create=True);p.start();self.addCleanup(p.stop)
        self.url='https://luxart.com/paveikslai/test/'
    def test_429_pauses_shared_limiter_before_retry(self):
        err=HTTPError(self.url,429,'slow down',{'Retry-After':'60'},None)
        with patch.object(importer.urllib.request,'urlopen',side_effect=[err,Response('<h1>Painting</h1>')]):
            importer.fetch(self.url)
        self.assertEqual(self.rate.rate,5)
        self.assertGreaterEqual(self.now,60)
    def test_cached_html_does_not_count_as_network_success(self):
        with patch.object(importer.urllib.request,'urlopen',return_value=Response('<h1>Painting</h1>')) as req:
            importer.fetch(self.url);importer.fetch(self.url)
        self.assertEqual(req.call_count,1)
        self.assertEqual(self.rate.successes,1)
    def test_challenge_html_not_cached_or_counted_as_success(self):
        with patch.object(importer.urllib.request,'urlopen',return_value=Response('<title>Just a moment...</title><div>Checking your browser</div>')):
            with self.assertRaises(RuntimeError):importer.fetch(self.url)
        self.assertEqual(list(Path(self.tmp.name).iterdir()),[])
        self.assertLess(self.rate.rate,10)
    def test_404_is_not_retried_or_used_to_slow_rate(self):
        with patch.object(importer.urllib.request,'urlopen',side_effect=HTTPError(self.url,404,'missing',{},None)) as req:
            with self.assertRaises(HTTPError):importer.fetch(self.url)
        self.assertEqual(req.call_count,1)
        self.assertEqual(self.rate.rate,10)
