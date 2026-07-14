# AI DiagNoise Demo

这是一个面向企业系统报错截图的 AI 诊断 Demo。用户上传报错截图并补充系统、菜单、时间、账号、单据号和操作步骤后，程序会把截图识别结果、页面接口映射、后端日志片段和历史案例一起交给 AI 分析，输出根因和处理建议。

## 当前能力

1. 页面接口映射：`data/interface_mapping.json` 维护前端页面、按钮、后端 API、后端服务、关键词之间的标准关系。
2. 后端日志关联：`data/log_sources.json` 维护系统、服务、服务器地址、日志路径、日志格式；Demo 使用 `data/sample_logs/` 下的本地样例日志模拟检索。
3. 报错截图上传：页面支持上传 PNG/JPG/WEBP，并填写系统名称、系统菜单、报错时间、操作人账号、单据号、操作步骤。
4. 截图内容识别：当前默认由多模态模型完成 OCR 和页面语义理解，`services/ocr_service.py` 已预留 PaddleOCR/RapidOCR 替换点。
5. 异常原因分析：`services/diagnosis_agent.py` 编排接口映射、日志检索、历史案例和模型调用，输出证据链、根因、解决方案，并可保存到 `data/history_cases.json`。

## 推荐目标架构

| 模块 | 推荐技术 | Demo 中的落点 |
| --- | --- | --- |
| 前端 | Vue3 + Element Plus | 当前为 Flask 模板，接口保持 `/analyze`、`/cases`，可平滑替换为 Vue3 |
| 后端 | Spring Boot + Spring AI 或 LangChain4j | 当前 Flask HTTP 层只做入参和响应，核心流程已拆到 service 层 |
| OCR | PaddleOCR / RapidOCR / 多模态模型 | `services/ocr_service.py` |
| LLM | Qwen3、DeepSeek、GPT-5.5，经统一模型网关 | `services/model_gateway.py`，支持 Anthropic 和 OpenAI-compatible 网关 |
| Agent 编排 | LangGraph、LangChain4j Agent 或 Spring AI Agent | `services/diagnosis_agent.py` |
| 向量知识库 | Milvus、Elasticsearch 向量检索、PostgreSQL + pgvector | 后续可替换历史案例读取逻辑 |
| 日志检索 | Elasticsearch / Loki，Demo 可 SSH + grep | `services/log_search.py` 当前为本地 grep-like 检索 |
| 配置中心 | MySQL，维护页面到接口到服务到日志路径映射 | `services/config_repository.py` 当前为 JSON 仓储 |
| 对象存储 | MinIO，保存截图和分析报告 | 当前临时保存上传文件，后续可在 `/analyze` 和 `/cases` 接入 MinIO |

## Local Run

```bash
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Then open `http://localhost:5000`.

## Model Gateway

默认使用 Anthropic：

```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_api_key_here
MODEL_GATEWAY_MODEL=claude-sonnet-4-6
```

如果你的 Qwen、DeepSeek 或 GPT 系列模型通过 OpenAI-compatible 网关暴露：

```env
AI_PROVIDER=openai_compatible
MODEL_GATEWAY_BASE_URL=https://your-gateway.example.com/v1
MODEL_GATEWAY_API_KEY=your_gateway_key
MODEL_GATEWAY_MODEL=your-vision-model
```

Optional environment variables: `MODEL_GATEWAY_MAX_TOKENS`, `FLASK_DEBUG`, `HOST`, `PORT`.

## Demo Input Example

可用以下上下文测试日志关联：

- 系统名称：采购管理系统
- 系统菜单：采购管理 > 采购订单 > 订单提交
- 报错时间：2026-06-30 15:06
- 操作人账号：zhangsan
- 单据号：PO202606300018
- 操作步骤：打开采购订单，点击提交后提示库存中心超时

## Public Deployment

Use these settings:

- Build command: `pip install -r requirements.txt`
- Start command: `waitress-serve --host=0.0.0.0 --port=$PORT app:app`
- Required environment variable: `ANTHROPIC_API_KEY` or `MODEL_GATEWAY_API_KEY`

Keep `FLASK_DEBUG=0` in production.
