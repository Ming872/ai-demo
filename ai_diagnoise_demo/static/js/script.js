const MAX_FILE_SIZE = 8 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
const ALLOWED_EXTENSIONS = new Set(["png", "jpg", "jpeg", "webp"]);

const state = {
  file: null,
  previewUrl: null,
  caseId: null,
  sections: [],
  context: {},
};

const $ = (id) => document.getElementById(id);

function setStatus(text, mode = "idle") {
  const statusText = $("status-text");
  const statusDot = $("status-dot");
  statusText.textContent = text;
  statusDot.classList.toggle("is-busy", mode === "busy");
  statusDot.classList.toggle("is-done", mode === "done");
  statusDot.classList.toggle("is-error", mode === "error");
}

function showError(message) {
  const errorMsg = $("error-msg");
  errorMsg.textContent = message;
  errorMsg.hidden = !message;
  if (message) setStatus("处理失败", "error");
}

function validateFile(file) {
  if (!file) return "请先选择一张报错截图。";

  const extension = file.name.includes(".")
    ? file.name.split(".").pop().toLowerCase()
    : "";

  if (!ALLOWED_TYPES.has(file.type) && !ALLOWED_EXTENSIONS.has(extension)) {
    return "仅支持 PNG、JPG、JPEG 或 WEBP 图片。";
  }

  if (file.size > MAX_FILE_SIZE) {
    return "文件过大，单个截图不能超过 8 MB。";
  }

  return "";
}

function syncInputFile(file) {
  const fileInput = $("file-input");
  if (!file) {
    fileInput.value = "";
    return;
  }

  try {
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;
  } catch (_error) {
    // Some older browsers do not allow assigning FileList. Submit uses state.file too.
  }
}

function setSelectedFile(file) {
  const validationError = validateFile(file);
  if (validationError) {
    clearSelectedFile();
    showError(validationError);
    return;
  }

  const previewImg = $("preview-img");
  const previewFilename = $("preview-filename");

  if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
  state.file = file;
  state.previewUrl = URL.createObjectURL(file);
  syncInputFile(file);

  previewImg.src = state.previewUrl;
  previewFilename.textContent = `${file.name} (${formatFileSize(file.size)})`;
  $("dropzone-empty").hidden = true;
  $("dropzone-preview").hidden = false;
  $("submit-btn").disabled = false;
  $("save-case-btn").hidden = true;
  showError("");
  setStatus("截图已选择", "done");
}

function clearSelectedFile() {
  if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
  state.file = null;
  state.previewUrl = null;
  syncInputFile(null);

  $("preview-img").removeAttribute("src");
  $("preview-filename").textContent = "";
  $("dropzone-empty").hidden = false;
  $("dropzone-preview").hidden = true;
  $("submit-btn").disabled = true;
  $("scan-line").hidden = true;
  setStatus("待上传");
}

function formatFileSize(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function renderSections(sections) {
  const list = $("results-list");
  list.replaceChildren();

  sections.forEach((section, index) => {
    const card = document.createElement("article");
    card.className = "section-card";

    const number = document.createElement("div");
    number.className = "section-card__index";
    number.textContent = section.number || String(index + 1);

    const content = document.createElement("div");
    const title = document.createElement("h3");
    title.className = "section-card__title";
    title.textContent = section.title || "诊断结果";

    const body = document.createElement("div");
    body.className = "section-card__body";
    body.textContent = section.content || "";

    content.append(title, body);
    card.append(number, content);
    list.append(card);
  });

  $("results").hidden = false;
  $("results-mode").textContent = `${sections.length} 个分析段落`;
}

async function submitAnalysis(event) {
  event.preventDefault();

  const validationError = validateFile(state.file || $("file-input").files[0]);
  if (validationError) {
    showError(validationError);
    return;
  }

  const form = $("analyze-form");
  const formData = new FormData(form);
  formData.set("image", state.file || $("file-input").files[0]);

  $("submit-btn").disabled = true;
  $("submit-label").textContent = "诊断中...";
  $("scan-line").hidden = false;
  $("save-case-btn").hidden = true;
  showError("");
  setStatus("AI 分析中", "busy");

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json().catch(() => ({}));

    if (!response.ok || !payload.success) {
      throw new Error(payload.error || "诊断请求失败，请稍后重试。");
    }

    state.caseId = payload.case_id;
    state.sections = payload.sections || [];
    state.context = payload.context || {};
    renderSections(state.sections);
    $("save-case-btn").hidden = false;
    setStatus("诊断完成", "done");
  } catch (error) {
    showError(error.message || "诊断请求失败，请稍后重试。");
  } finally {
    $("submit-btn").disabled = !state.file;
    $("submit-label").textContent = "开始诊断";
    $("scan-line").hidden = true;
  }
}

async function saveCase() {
  if (!state.sections.length) {
    showError("没有可沉淀的分析结果。");
    return;
  }

  const button = $("save-case-btn");
  button.disabled = true;
  button.textContent = "保存中...";
  showError("");

  try {
    const response = await fetch("/cases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        case_id: state.caseId,
        sections: state.sections,
        context: state.context,
      }),
    });
    const payload = await response.json().catch(() => ({}));

    if (!response.ok || !payload.success) {
      throw new Error(payload.error || "案例保存失败，请稍后重试。");
    }

    button.textContent = `已沉淀案例 ${payload.case_id}`;
    setStatus("案例已保存", "done");
  } catch (error) {
    button.disabled = false;
    button.textContent = "确认并沉淀案例";
    showError(error.message || "案例保存失败，请稍后重试。");
  }
}

function bindDropzone() {
  const dropzone = $("dropzone");
  const fileInput = $("file-input");
  const removeFile = $("remove-file");

  dropzone.addEventListener("click", (event) => {
    if (event.target === removeFile) return;
    fileInput.click();
  });

  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", () => {
    setSelectedFile(fileInput.files[0]);
  });

  removeFile.addEventListener("click", (event) => {
    event.stopPropagation();
    clearSelectedFile();
    showError("");
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      event.stopPropagation();
      dropzone.classList.add("is-dragover");
      if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
    });
  });

  ["dragleave", "dragend", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      event.stopPropagation();
      dropzone.classList.remove("is-dragover");
    });
  });

  dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer?.files?.[0];
    setSelectedFile(file);
  });

  document.addEventListener("dragover", (event) => event.preventDefault());
  document.addEventListener("drop", (event) => event.preventDefault());
}

function init() {
  bindDropzone();
  $("analyze-form").addEventListener("submit", submitAnalysis);
  $("save-case-btn").addEventListener("click", saveCase);
  setStatus("待上传");
}

document.addEventListener("DOMContentLoaded", init);
