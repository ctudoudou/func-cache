import unittest
import os
from func_cache.cache import Cache
import time


@Cache(cache_dir="cache")
def add(x, y):
    time.sleep(5)
    return x + y


class TestCache(unittest.TestCase):
    def test_cache(self):
        add(1, 2)
        self.assertTrue(os.path.exists("cache"))
        self.assertTrue(os.path.exists("cache/3713081631934410651"))
        with open("cache/3713081631934410651") as cache_file:
            self.assertEqual(cache_file.read(), "3")
        os.remove("cache/3713081631934410651")
        os.rmdir("cache")
