import unittest
from datetime import datetime, timedelta

import pytz

from cache_manager import RSSCacheManager


PACIFIC = pytz.timezone("America/Los_Angeles")


class RSSCacheManagerTests(unittest.TestCase):
    def setUp(self):
        RSSCacheManager._rss_cache.clear()
        RSSCacheManager._rss_timestamps.clear()

    def tearDown(self):
        RSSCacheManager._rss_cache.clear()
        RSSCacheManager._rss_timestamps.clear()

    def test_cache_timestamps_are_timezone_aware(self):
        RSSCacheManager.set_feed_cache(1, "content")

        self.assertIsNotNone(RSSCacheManager._rss_timestamps[1].tzinfo)

    def test_cache_expires_after_an_hour_boundary(self):
        now = datetime.now(PACIFIC)
        RSSCacheManager._rss_cache[1] = "old content"
        RSSCacheManager._rss_timestamps[1] = now - timedelta(hours=2)

        self.assertIsNone(RSSCacheManager.get_feed_cache(1))


if __name__ == "__main__":
    unittest.main()
