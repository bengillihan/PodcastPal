import unittest
from datetime import datetime

import pytz

from recurring import effective_annual_release_date


PACIFIC = pytz.timezone("America/Los_Angeles")


class EffectiveAnnualReleaseDateTests(unittest.TestCase):
    def local(self, year, month, day, hour=0, minute=0):
        return PACIFIC.localize(datetime(year, month, day, hour, minute))

    def test_advances_to_current_year_after_anniversary(self):
        original = self.local(2024, 3, 15, 8, 30)
        now = self.local(2026, 9, 1, 8, 0)

        result = effective_annual_release_date(original, now)

        self.assertEqual(result, self.local(2026, 3, 15, 8, 30))

    def test_uses_previous_occurrence_before_anniversary(self):
        original = self.local(2025, 12, 15, 8, 30)
        now = self.local(2026, 9, 1, 8, 0)

        result = effective_annual_release_date(original, now)

        self.assertEqual(result, self.local(2025, 12, 15, 8, 30))

    def test_advances_at_the_exact_release_time(self):
        original = self.local(2025, 9, 1, 8, 30)
        now = self.local(2026, 9, 1, 8, 30)

        result = effective_annual_release_date(original, now)

        self.assertEqual(result, self.local(2026, 9, 1, 8, 30))

    def test_february_29_uses_february_28_in_non_leap_year(self):
        original = self.local(2024, 2, 29, 7, 0)
        now = self.local(2026, 3, 1, 0, 0)

        result = effective_annual_release_date(original, now)

        self.assertEqual(result, self.local(2026, 2, 28, 7, 0))

    def test_preserves_local_time_when_dst_offset_changes(self):
        original = self.local(2024, 3, 10, 1, 30)
        now = self.local(2025, 4, 1, 0, 0)

        result = effective_annual_release_date(original, now)

        self.assertEqual(result, self.local(2025, 3, 10, 1, 30))
        self.assertNotEqual(result.utcoffset(), original.utcoffset())

    def test_rejects_mixed_timezone_awareness(self):
        with self.assertRaises(ValueError):
            effective_annual_release_date(
                datetime(2025, 1, 1),
                self.local(2026, 1, 2),
            )


if __name__ == "__main__":
    unittest.main()
