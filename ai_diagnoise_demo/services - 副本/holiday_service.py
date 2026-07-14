from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional, Set


class HolidayService:
    """A lightweight holiday service for Chinese public holidays and weekend handling."""

    def __init__(self) -> None:
        self._holidays: Dict[int, Set[date]] = self._build_holiday_table()
        self._makeup_workdays: Dict[int, Set[date]] = self._build_makeup_workday_table()

    def _build_holiday_table(self) -> Dict[int, Set[date]]:
        holiday_dates: Dict[int, Set[date]] = {}
        for year in range(2024, 2027):
            holiday_dates[year] = set()

        holiday_dates[2024].update({
            date(2024, 1, 1),
            date(2024, 2, 10),
            date(2024, 2, 11),
            date(2024, 2, 12),
            date(2024, 2, 13),
            date(2024, 2, 14),
            date(2024, 2, 15),
            date(2024, 2, 16),
            date(2024, 2, 17),
            date(2024, 4, 4),
            date(2024, 4, 5),
            date(2024, 4, 6),
            date(2024, 5, 1),
            date(2024, 5, 2),
            date(2024, 5, 3),
            date(2024, 5, 4),
            date(2024, 5, 5),
            date(2024, 6, 8),
            date(2024, 6, 9),
            date(2024, 6, 10),
            date(2024, 9, 15),
            date(2024, 9, 16),
            date(2024, 9, 17),
            date(2024, 10, 1),
            date(2024, 10, 2),
            date(2024, 10, 3),
            date(2024, 10, 4),
            date(2024, 10, 5),
            date(2024, 10, 6),
            date(2024, 10, 7),
        })

        holiday_dates[2025].update({
            date(2025, 1, 1),
            date(2025, 1, 28),
            date(2025, 1, 29),
            date(2025, 1, 30),
            date(2025, 1, 31),
            date(2025, 2, 1),
            date(2025, 2, 2),
            date(2025, 2, 3),
            date(2025, 2, 4),
            date(2025, 4, 4),
            date(2025, 4, 5),
            date(2025, 4, 6),
            date(2025, 5, 1),
            date(2025, 5, 2),
            date(2025, 5, 3),
            date(2025, 5, 4),
            date(2025, 5, 5),
            date(2025, 5, 31),
            date(2025, 6, 1),
            date(2025, 6, 2),
            date(2025, 10, 1),
            date(2025, 10, 2),
            date(2025, 10, 3),
            date(2025, 10, 4),
            date(2025, 10, 5),
            date(2025, 10, 6),
            date(2025, 10, 7),
            date(2025, 10, 8),
        })

        holiday_dates[2026].update({
            date(2026, 1, 1),
            date(2026, 1, 2),
            date(2026, 1, 3),
            date(2026, 2, 15),
            date(2026, 2, 16),
            date(2026, 2, 17),
            date(2026, 2, 18),
            date(2026, 2, 19),
            date(2026, 2, 20),
            date(2026, 2, 21),
            date(2026, 2, 22),
            date(2026, 2, 23),
            date(2026, 4, 4),
            date(2026, 4, 5),
            date(2026, 4, 6),
            date(2026, 5, 1),
            date(2026, 5, 2),
            date(2026, 5, 3),
            date(2026, 5, 4),
            date(2026, 5, 5),
            date(2026, 6, 19),
            date(2026, 6, 20),
            date(2026, 6, 21),
        })

        return holiday_dates

    def _build_makeup_workday_table(self) -> Dict[int, Set[date]]:
        makeup_workdays: Dict[int, Set[date]] = {year: set() for year in range(2024, 2027)}
        makeup_workdays[2024].update({
            date(2024, 2, 4),
            date(2024, 2, 18),
            date(2024, 4, 7),
            date(2024, 4, 28),
            date(2024, 5, 11),
            date(2024, 9, 14),
            date(2024, 9, 29),
            date(2024, 10, 12),
        })
        makeup_workdays[2025].update({
            date(2025, 1, 26),
            date(2025, 2, 8),
            date(2025, 4, 27),
            date(2025, 9, 28),
            date(2025, 10, 11),
        })
        makeup_workdays[2026].update({
            date(2026, 1, 4),
            date(2026, 2, 14),
            date(2026, 2, 28),
            date(2026, 5, 9),
        })
        return makeup_workdays

    def is_holiday(self, day: date | str | datetime) -> bool:
        target_date = self._coerce_date(day)
        return target_date in self._holidays.get(target_date.year, set())

    def is_workday(self, day: date | str | datetime) -> bool:
        target_date = self._coerce_date(day)
        if self.is_holiday(target_date):
            return False
        if target_date in self._makeup_workdays.get(target_date.year, set()):
            return True
        return target_date.weekday() < 5

    def is_non_working_day(self, day: date | str | datetime) -> bool:
        target_date = self._coerce_date(day)
        if self.is_holiday(target_date):
            return True
        if target_date in self._makeup_workdays.get(target_date.year, set()):
            return False
        return target_date.weekday() >= 5

    def _coerce_date(self, day: date | str | datetime) -> date:
        if isinstance(day, datetime):
            return day.date()
        if isinstance(day, date):
            return day
        return datetime.strptime(day, "%Y-%m-%d").date()

    def describe(self, day: date | str | datetime) -> str:
        target_date = self._coerce_date(day)
        if target_date in self._holidays.get(target_date.year, set()):
            return "holiday"
        if target_date.weekday() >= 5:
            return "weekend"
        return "weekday"

    def get_holiday_table(self, year: int) -> List[dict]:
        dates = sorted(self._holidays.get(year, set()))
        return [{"date": day.strftime("%Y-%m-%d"), "name": "public_holiday"} for day in dates]
