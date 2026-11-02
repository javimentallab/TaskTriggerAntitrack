"""When a task fires, and how the interface language is chosen. No window is opened."""
import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["TTA_LANG"] = "es"

import tasktriggerantitrack as tta  # noqa: E402
import tta_lang  # noqa: E402

NOW = datetime(2026, 11, 2, 12, 0, 0)


class Fixed(unittest.TestCase):
    def test_later_today(self):
        self.assertEqual(tta.compute_next({"time": "13:30"}, NOW), datetime(2026, 11, 2, 13, 30))

    def test_already_passed_goes_to_tomorrow(self):
        self.assertEqual(tta.compute_next({"time": "11:59"}, NOW), datetime(2026, 11, 3, 11, 59))

    def test_exactly_now_goes_to_tomorrow(self):
        self.assertEqual(tta.compute_next({"time": "12:00"}, NOW), datetime(2026, 11, 3, 12, 0))

    def test_end_of_the_year(self):
        self.assertEqual(tta.compute_next({"time": "09:00"}, datetime(2026, 12, 31, 23, 0)), datetime(2027, 1, 1, 9, 0))

    def test_spaces_around_the_time(self):
        self.assertEqual(tta.compute_next({"time": " 13:30 "}, NOW), datetime(2026, 11, 2, 13, 30))


class RandomWindow(unittest.TestCase):
    def alarm(self, start, end):
        return {"time_mode": "range", "start_time": start, "end_time": end}

    def check_many(self, alarm, lo, hi):
        for _i in range(200):
            t = tta.compute_next(alarm, NOW)
            self.assertTrue(lo <= t <= hi, t)

    def test_window_still_to_come(self):
        self.check_many(self.alarm("14:00", "15:00"), datetime(2026, 11, 2, 14), datetime(2026, 11, 2, 15))

    def test_never_in_the_past_when_the_window_has_started(self):
        self.check_many(self.alarm("11:00", "13:00"), NOW, datetime(2026, 11, 2, 13))

    def test_window_already_over_goes_to_tomorrow(self):
        self.check_many(self.alarm("08:00", "09:00"), datetime(2026, 11, 3, 8), datetime(2026, 11, 3, 9))

    def test_window_across_midnight(self):
        self.check_many(self.alarm("23:00", "01:00"), datetime(2026, 11, 2, 23), datetime(2026, 11, 3, 1))

    def test_uses_the_whole_window(self):
        seen = {tta.compute_next(self.alarm("14:00", "15:00"), NOW) for _i in range(50)}
        self.assertGreater(len(seen), 1)
        self.assertLessEqual(max(seen) - min(seen), timedelta(hours=1))


class Parsing(unittest.TestCase):
    def test_hours_and_minutes(self):
        self.assertEqual(tta._hm("07:05"), (7, 5))

    def test_bad_time_is_an_error(self):
        with self.assertRaises(ValueError):
            tta._hm("nonsense")

    def test_iso(self):
        self.assertEqual(tta._parse_iso("2026-11-02 12:00:00"), NOW)

    def test_bad_iso_gives_none(self):
        for bad in ("yesterday", "", None, 5):
            self.assertIsNone(tta._parse_iso(bad))

    def test_wide_characters_count_double(self):
        self.assertEqual(tta._text_cols("abc"), 3)
        self.assertEqual(tta._text_cols("名前"), 4)


class Language(unittest.TestCase):
    def test_all_fifteen(self):
        for code in "en es pt fr de it nl pl ru uk zh ja ko th hi".split():
            self.assertIn(code, tta_lang.SUPPORTED)

    def test_every_language_has_every_text(self):
        for lang, table in tta_lang.TABLES.items():
            self.assertEqual(set(table), set(tta_lang.SOURCE), lang)

    def test_option_wins_over_environment(self):
        with mock.patch.dict(os.environ, {"TTA_LANG": "fr"}):
            self.assertEqual(tta_lang.pick_lang(["x", "--lang", "de"]), "de")

    def test_environment(self):
        with mock.patch.dict(os.environ, {"TTA_LANG": "fr"}):
            self.assertEqual(tta_lang.pick_lang(["x"]), "fr")

    def test_region_is_ignored(self):
        self.assertEqual(tta_lang.pick_lang(["x", "--lang", "zh-CN"]), "zh")

    def test_unknown_falls_back_to_english(self):
        self.assertEqual(tta_lang.pick_lang(["x", "--lang", "tlh"]), "en")

    def test_option_without_value_does_not_crash(self):
        with mock.patch.dict(os.environ, {"TTA_LANG": "it"}):
            self.assertEqual(tta_lang.pick_lang(["x", "--lang"]), "it")


if __name__ == "__main__":
    unittest.main()
