"""Diagnosis orchestration: context retrieval, prompt building and parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from services.config_repository import ConfigRepository
from services.log_search import LocalLogSearchService
from services.model_gateway import ModelGateway
from services.ocr_service import OcrService

SECTION_PATTERN = re.compile(r"(?m)^\s*(\d+)\.\s*(?:\[([^\]]+)\]|(.+?))\s*:\s*")


class DiagnosisAgent:
    """Small agent-style orchestrator for the diagnosis workflow."""

    def __init__(
        self,
        base_dir: Path,
        config_repository: ConfigRepository,
        model_gateway: ModelGateway,
        ocr_service: OcrService,
        log_time_window_minutes: int = 30,
        max_log_lines: int = 80,
    ) -> None:
        self.base_dir = base_dir
        self.config_repository = config_repository
        self.model_gateway = model_gateway
        self.ocr_service = ocr_service
        self.log_time_window_minutes = log_time_window_minutes
        self.max_log_lines = max_log_lines

    def analyze(
        self,
        image_path: Path,
        media_type: str,
        context: dict[str, str],
    ) -> dict[str, Any]:
        mappings = self.select_interface_mappings(context)
        logs = LocalLogSearchService(
            self.base_dir,
            self.config_repository.log_sources(),
            self.log_time_window_minutes,
            self.max_log_lines,
        ).search(context, mappings)
        history_cases = self.config_repository.history_cases()
        ocr_hint = self.ocr_service.extract(image_path)
        prompt = self.build_prompt(context, mappings, logs, history_cases, ocr_hint)
        raw_result = self.model_gateway.analyze_image(image_path, prompt, media_type)

        return {
            "sections": parse_sections(raw_result),
            "matched_mappings": mappings,
            "log_sources": logs,
            "context": context,
            "ocr_hint": ocr_hint,
        }

    def select_interface_mappings(self, context: dict[str, str]) -> list[dict[str, Any]]:
        mappings = self.config_repository.interface_mappings()
        scored = sorted(
            ((score_mapping_item(item, context), item) for item in mappings),
            key=lambda pair: pair[0],
            reverse=True,
        )
        ranked = [item for _score, item in scored]
        selected = [item for score, item in scored if score > 0]
        return (selected or ranked)[:5]

    @staticmethod
    def build_prompt(
        context: dict[str, str],
        mappings: list[dict[str, Any]],
        logs: list[dict[str, str]],
        history_cases: list[dict[str, Any]],
        ocr_hint: dict[str, str],
    ) -> str:
        prompt_context = {
            "用户补充信息": context,
            "OCR预处理结果": ocr_hint,
            "页面接口映射候选": mappings,
            "日志检索结果": logs,
            "历史案例参考": history_cases[-5:],
        }
        return (
            "你是企业系统故障诊断专家。用户上传了一张系统报错截图，请先基于截图做 OCR "
            "和页面语义理解，再结合用户补充信息、页面接口映射、后端日志和历史案例定位异常原因。\n\n"
            f"上下文数据如下：\n{json.dumps(prompt_context, ensure_ascii=False, indent=2)}\n\n"
            "请严格按以下结构输出，标题必须保留：\n"
            "1. [截图内容识别]: 识别页面名称、菜单路径、错误提示、错误码、单据号、操作时间等关键信息；未知项写“未识别”。\n"
            "2. [可能出错接口和服务]: 从页面接口映射中给出最可能的 API、按钮、后端服务、置信度和依据。\n"
            "3. [后端日志关联]: 总结命中的日志来源、关键日志行、trace/request 信息和异常堆栈线索。\n"
            "4. [异常原因分析]: 判断最可能根因，说明证据链；如果证据不足，列出还需补充的日志或字段。\n"
            "5. [解决方案和处理建议]: 给出业务处理、技术修复、回滚/重试、监控告警和预防建议。\n"
            "6. [历史案例沉淀建议]: 生成一个可沉淀案例，包含标题、故障现象、根因、处置步骤、关键词。"
        )


def score_mapping_item(item: dict[str, Any], context: dict[str, str]) -> int:
    haystack = " ".join(
        str(value)
        for value in [
            item.get("system_name"),
            item.get("page_name"),
            item.get("menu_path"),
            item.get("button_name"),
            item.get("api"),
            item.get("service"),
            item.get("backend_service"),
            item.get("keywords"),
        ]
    ).lower()
    needles = [
        context.get("system_name", ""),
        context.get("menu_path", ""),
        context.get("operation_steps", ""),
        context.get("document_no", ""),
    ]
    score = 0
    for needle in needles:
        for token in re.split(r"[\s>/,，。；;、]+", needle.lower()):
            if token and token in haystack:
                score += 2 if len(token) > 2 else 1
    return score


def parse_sections(result_text: str) -> list[dict[str, str]]:
    matches = list(SECTION_PATTERN.finditer(result_text))
    if not matches:
        return [{"number": "", "title": "诊断结果", "content": result_text.strip()}]

    sections = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(result_text)
        sections.append(
            {
                "number": match.group(1),
                "title": (match.group(2) or match.group(3) or "诊断结果").strip(),
                "content": result_text[start:end].strip(),
            }
        )
    return sections
