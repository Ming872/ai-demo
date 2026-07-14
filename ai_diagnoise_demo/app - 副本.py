"""Flask HTTP layer for AI-assisted error screenshot diagnosis."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from services.config_repository import ConfigRepository
from services.diagnosis_agent import DiagnosisAgent
from services.holiday_service import HolidayService
from services.model_gateway import ModelGateway, ModelGatewayError
from services.ocr_service import OcrService

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_CONTENT_LENGTH = 8 * 1024 * 1024
LOG_TIME_WINDOW_MINUTES = 30
MAX_LOG_LINES = 80

MEDIA_TYPE_MAP = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
UPLOAD_FOLDER.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

config_repository = ConfigRepository(DATA_DIR)
holiday_service = HolidayService()
diagnosis_agent = DiagnosisAgent(
    BASE_DIR,
    config_repository,
    ModelGateway(),
    OcrService(),
    LOG_TIME_WINDOW_MINUTES,
    MAX_LOG_LINES,
)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[-1].lower() in ALLOWED_EXTENSIONS


def normalize_text(value: str | None) -> str:
    return (value or "").strip()


def collect_context_from_form() -> dict[str, str]:
    return {
        "system_name": normalize_text(request.form.get("system_name")),
        "menu_path": normalize_text(request.form.get("menu_path")),
        "error_time": normalize_text(request.form.get("error_time")),
        "operator": normalize_text(request.form.get("operator")),
        "document_no": normalize_text(request.form.get("document_no")),
        "operation_steps": normalize_text(request.form.get("operation_steps")),
    }


@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(_exc):
    return jsonify(success=False, error="文件过大，单个截图不能超过 8 MB。"), 413


@app.route("/")
def index():
    mappings = config_repository.interface_mappings()
    log_sources = config_repository.log_sources()
    return render_template("index.html", mapping_count=len(mappings), log_source_count=len(log_sources))


@app.route("/holiday-check")
def holiday_check():
    sample_day = "2024-02-10"
    return jsonify(
        success=True,
        date=sample_day,
        is_holiday=holiday_service.is_holiday(sample_day),
        is_workday=holiday_service.is_workday(sample_day),
        is_non_working_day=holiday_service.is_non_working_day(sample_day),
        description=holiday_service.describe(sample_day),
    )


@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("image")

    if not file or file.filename == "":
        return jsonify(success=False, error="请先选择一张报错截图。"), 400

    if not allowed_file(file.filename):
        return jsonify(success=False, error="仅支持 PNG、JPG、JPEG 或 WEBP 图片。"), 400

    filename = secure_filename(file.filename)
    if not filename:
        return jsonify(success=False, error="文件名无效，请重新选择截图。"), 400

    context = collect_context_from_form()
    ext = filename.rsplit(".", 1)[-1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    filepath = UPLOAD_FOLDER / stored_name
    file.save(filepath)

    media_type = MEDIA_TYPE_MAP.get(ext, "image/png")

    try:
        result = diagnosis_agent.analyze(filepath, media_type, context)
    except ModelGatewayError as exc:
        return jsonify(success=False, error=str(exc)), 502
    finally:
        filepath.unlink(missing_ok=True)

    case_id = uuid.uuid4().hex[:12]
    return jsonify(
        success=True,
        case_id=case_id,
        **result,
    )


@app.route("/cases", methods=["POST"])
def save_case():
    payload = request.get_json(silent=True) or {}
    sections = payload.get("sections") or []
    context = payload.get("context") or {}
    case_id = payload.get("case_id") or uuid.uuid4().hex[:12]

    if not sections:
        return jsonify(success=False, error="没有可沉淀的分析结果。"), 400

    total = config_repository.append_case(case_id, context, sections)
    return jsonify(success=True, case_id=case_id, total=total)


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    app.run(debug=debug, host=host, port=port)
