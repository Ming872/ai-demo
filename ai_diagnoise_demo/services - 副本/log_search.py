"""Log retrieval service with a local grep-like demo backend."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

LOG_TIME_PATTERN = re.compile(r"(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})")


class LocalLogSearchService:
    """Search local sample logs; production can swap this for ES, Loki or SSH."""

    def __init__(
        self,
        base_dir: Path,
        sources: list[dict[str, Any]],
        time_window_minutes: int = 30,
        max_log_lines: int = 80,
    ) -> None:
        self.base_dir = base_dir
        self.sources = sources
        self.time_window_minutes = time_window_minutes
        self.max_log_lines = max_log_lines

    def search(self, context: dict[str, str], mappings: list[dict[str, Any]]) -> list[dict[str, str]]:
        center_time = self._parse_datetime(context.get("error_time", ""))
        keywords = self._collect_keywords(context, mappings)
        results: list[dict[str, str]] = []

        for source in self.sources:
            local_path = source.get("local_path", "")
            log_path = self.base_dir / local_path
            if not local_path or not log_path.exists():
                continue

            lines = log_path.read_text(
                encoding=source.get("encoding", "utf-8"),
                errors="ignore",
            ).splitlines()
            matched_lines = self._match_lines(lines, keywords, center_time)
            if matched_lines:
                results.append(
                    {
                        "system": source.get("system_name", ""),
                        "service": source.get("service", ""),
                        "server": source.get("server", ""),
                        "path": source.get("path", local_path),
                        "format": source.get("format", ""),
                        "content": "\n".join(matched_lines),
                    }
                )
        return results

    def _match_lines(
        self,
        lines: list[str],
        keywords: set[str],
        center_time: datetime | None,
    ) -> list[str]:
        matched_lines: list[str] = []
        for line in lines:
            lower_line = line.lower()
            keyword_hit = not keywords or any(keyword in lower_line for keyword in keywords)
            if keyword_hit and self._line_in_time_window(line, center_time):
                matched_lines.append(line)
            if len(matched_lines) >= self.max_log_lines:
                break
        return matched_lines

    def _collect_keywords(self, context: dict[str, str], mappings: list[dict[str, Any]]) -> set[str]:
        keywords = {
            context.get("operator", ""),
            context.get("document_no", ""),
            context.get("system_name", ""),
        }
        for item in mappings:
            keywords.update(
                str(value)
                for value in [
                    item.get("api"),
                    item.get("service"),
                    item.get("backend_service"),
                    item.get("trace_keyword"),
                ]
                if value
            )
            keywords.update(item.get("keywords", []))
        return {keyword.lower() for keyword in keywords if keyword}

    def _line_in_time_window(self, line: str, center: datetime | None) -> bool:
        if center is None:
            return True
        match = LOG_TIME_PATTERN.search(line)
        if not match:
            return True
        try:
            ts = datetime.strptime(match.group("ts").replace("T", " "), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return True
        start = center - timedelta(minutes=self.time_window_minutes)
        end = center + timedelta(minutes=self.time_window_minutes)
        return start <= ts <= end

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        if not value:
            return None
        candidates = [value, value.replace("/", "-"), value.replace("T", " ")]
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
        for candidate in candidates:
            for fmt in formats:
                try:
                    parsed = datetime.strptime(candidate, fmt)
                    if fmt == "%Y-%m-%d":
                        return parsed.replace(hour=12)
                    return parsed
                except ValueError:
                    continue
        return None
