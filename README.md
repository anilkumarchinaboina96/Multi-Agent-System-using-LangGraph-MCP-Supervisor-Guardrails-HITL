# ✈️ AI Travel Planning Agent (LangGraph + MCP + HITL)

Build smart, reviewable travel plans with a **multi-agent workflow** powered by **LangGraph**, **MCP tools**, and **human approval**.

This project demonstrates how to combine:
- 🤖 Specialist agents (flight, hotel, weather, budget, itinerary)
- 🧭 A supervisor router
- 🛡️ Guardrails for request validation
- 👤 Human-in-the-loop (HITL) approval before final output

---

## 🌟 Highlights

- Modern FastAPI web app for interactive trip planning
- Multi-step travel plan generation with approval flow
- MCP integrations for external tools/services
- Clear, structured API endpoints for frontend/backend flow
- OpenAI-based LLM integration via LangChain

---

## 🗂️ Project Structure

- `app.py` — FastAPI app and HTTP routes
- `backend.py` — LangGraph workflow, agents, and orchestration logic
- `mcp_client.py` — MCP client/tool integrations and helper methods
- `custom_weather_mcp_server.py` — example MCP weather server
- `templates/`, `static/` — frontend UI assets

---

## ✅ Prerequisites

- Python 3.10+
- Git
- Virtual environment (`venv` recommended)

---

## ⚙️ Quick Start (Windows)

1) Create and activate virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
pip install -r requirements.txt
```

3) Run the app

```powershell
python app.py
```

Alternative:

```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

4) Open in browser

`http://127.0.0.1:8000`

---

## 🔌 API Endpoints

- `POST /api/travel`
  Start or continue a travel planning thread.
  Payload: `{ "message": "<prompt>", "thread_id": "optional" }`

- `POST /api/travel/approve`
  Approve or revise a draft itinerary.
  Payload: `{ "thread_id": "<id>", "approved": true|false, "feedback": "optional" }`

- `GET /health`
  Health status and enabled features.

- `GET /metrics`
  Lightweight in-process API metrics (request counts, errors, average latency by path).

---

## 🔐 Environment Configuration

Use a `.env` file (never commit real secrets).

Required LLM settings:
- `OPENAI_API_KEY` — OpenAI API key
- `OPENAI_MODEL` — model name (default in code: `gpt-5.2`)

Optional token/cost tuning:
- `OPENAI_EXTRACT_MAX_TOKENS` — lightweight extraction output cap (default: `64`)

Other keys (as needed by MCP/tooling in this project):
- `TAVILY_API_KEY`
- `AVIATIONSTACK_API_KEY` (or `AVIATION_STACK_API_KEY`)
- `OPENWEATHER_API_KEY`
- `DATABASE_URL`

---

## 🧪 Development Notes

- `nest_asyncio` is applied in `app.py` so sync wrappers can call async MCP helpers.
- The workflow is designed to pause for HITL approval and resume safely.
- If requests are long-running, frontend timeout handling shows clear retry messages.
- API responses include an `X-Request-ID` header for request tracing in logs.

---

## 🤝 Contributing

Contributions are welcome! Open an issue or submit a pull request for:
- bug fixes
- UX improvements
- new MCP adapters
- performance/cost optimizations

## 🙌 Acknowledgements

Built as a practical demo of **LangGraph + MCP + Guardrails + HITL** patterns for real-world agentic applications.
