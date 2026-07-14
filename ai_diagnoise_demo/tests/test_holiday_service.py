import unittest
from datetime import date

from services.holiday_service import HolidayService


class HolidayServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = HolidayService()

    def test_detects_public_holiday(self) -> None:
        self.assertTrue(self.service.is_holiday(date(2024, 1, 1)))
        self.assertTrue(self.service.is_holiday(date(2025, 5, 1)))

    def test_detects_makeup_workday(self) -> None:
        self.assertFalse(self.service.is_holiday(date(2024, 2, 4)))
        self.assertTrue(self.service.is_workday(date(2024, 2, 4)))
        self.assertFalse(self.service.is_non_working_day(date(2024, 2, 4)))

    def test_spring_festival_and_labor_day_rules(self) -> None:
        self.assertTrue(self.service.is_holiday(date(2024, 2, 10)))
        self.assertTrue(self.service.is_holiday(date(2025, 5, 1)))
        self.assertFalse(self.service.is_holiday(date(2025, 2, 8)))
        self.assertFalse(self.service.is_holiday(date(2025, 5, 11)))
        self.assertTrue(self.service.is_workday(date(2025, 2, 8)))
        self.assertFalse(self.service.is_workday(date(2025, 5, 11)))
        self.assertFalse(self.service.is_non_working_day(date(2025, 2, 8)))
        self.assertTrue(self.service.is_non_working_day(date(2025, 5, 11)))
        self.assertTrue(self.service.is_workday(date(2024, 4, 28)))

    def test_weekends_are_non_working_days(self) -> None:
        self.assertTrue(self.service.is_non_working_day(date(2024, 1, 6)))
        self.assertFalse(self.service.is_workday(date(2024, 1, 6)))

    def test_unknown_date_is_regular_workday(self) -> None:
        self.assertFalse(self.service.is_holiday(date(2024, 7, 1)))
        self.assertFalse(self.service.is_non_working_day(date(2024, 7, 1)))
        self.assertTrue(self.service.is_workday(date(2024, 7, 1)))


if __name__ == "__main__":
    unittest.main()
