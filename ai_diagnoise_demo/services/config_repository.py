"""Configuration repository for page mappings, log sources and cases."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from utils.json_store import load_json, save_json


class ConfigRepository:
    """File-backed repository that can later be replaced by MySQL."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.interface_mapping_file = data_dir / "interface_mapping.json"
        self.log_sources_file = data_dir / "log_sources.json"
        self.history_cases_file = data_dir / "history_cases.json"

    def interface_mappings(self) -> list[dict[str, Any]]:
        return load_json(self.interface_mapping_file, [])

    def log_sources(self) -> list[dict[str, Any]]:
        return load_json(self.log_sources_file, [])

    def history_cases(self) -> list[dict[str, Any]]:
        return load_json(self.history_cases_file, [])

    def append_case(self, case_id: str, context: dict[str, str], sections: list[dict[str, str]]) -> int:
        cases = self.history_cases()
        cases.append(
            {
                "case_id": case_id,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "context": context,
                "sections": sections,
            }
        )
        save_json(self.history_cases_file, cases)
        return len(cases)
