from pathlib import Path
from collections import defaultdict
import logging
import time
import uuid

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from backend import run_travel_agent, resume_travel_agent

# This is kept from the original project to allow the existing synchronous
# agent functions to call async MCP helpers inside FastAPI.
import nest_asyncio

nest_asyncio.apply()


if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        ),
    )

logger = logging.getLogger("tripmate.api")

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="TripMate AI",
    description=(
        "LangGraph Multi-Agent Travel Planner with Supervisor, Guardrails, "
        "Human-in-the-Loop, and FastAPI Frontend"
    ),
    version="2.0.0",
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


REQUEST_METRICS: dict[str, object] = {
    "requests_total": 0,
    "errors_total": 0,
    "by_path": defaultdict(
        lambda: {
            "count": 0,
            "errors": 0,
            "total_duration_ms": 0.0,
        }
    ),
}


class TravelRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ApprovalRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    approved: bool
    feedback: str = ""


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id

    start = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        path_metrics = REQUEST_METRICS["by_path"][request.url.path]
        path_metrics["count"] += 1
        path_metrics["errors"] += 1
        path_metrics["total_duration_ms"] += duration_ms
        REQUEST_METRICS["requests_total"] += 1
        REQUEST_METRICS["errors_total"] += 1

        logger.exception(
            "Unhandled request error request_id=%s method=%s path=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )

        response = JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error.",
                "request_id": request_id,
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response

    duration_ms = (time.perf_counter() - start) * 1000
    path_metrics = REQUEST_METRICS["by_path"][request.url.path]
    path_metrics["count"] += 1
    path_metrics["total_duration_ms"] += duration_ms
    REQUEST_METRICS["requests_total"] += 1

    if response.status_code >= 500:
        path_metrics["errors"] += 1
        REQUEST_METRICS["errors_total"] += 1

    logger.info(
        "request_id=%s method=%s path=%s status=%d duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@app.post("/api/travel")
async def travel_planner(request: Request, request_data: TravelRequest):
    try:
        user_message = request_data.message.strip()

        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Message cannot be empty.",
                },
            )

        result = run_travel_agent(
            user_input=user_message,
            thread_id=request_data.thread_id,
        )

        return JSONResponse(
            content={
                "success": True,
                **result,
            }
        )

    except Exception as exc:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(
            "Travel planner failed request_id=%s",
            request_id,
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error.",
                "request_id": request_id,
            },
        )


@app.post("/api/travel/approve")
async def approve_travel_plan(request: Request, request_data: ApprovalRequest):
    try:
        if not request_data.approved and not request_data.feedback.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Please provide revision feedback when rejecting the draft.",
                },
            )

        result = resume_travel_agent(
            thread_id=request_data.thread_id,
            approved=request_data.approved,
            feedback=request_data.feedback,
        )

        return JSONResponse(
            content={
                "success": True,
                **result,
            }
        )

    except Exception as exc:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(
            "Approval flow failed request_id=%s",
            request_id,
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error.",
                "request_id": request_id,
            },
        )


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "TripMate AI API is running",
        "features": [
            "supervisor_agent",
            "input_guardrail",
            "human_in_the_loop",
        ],
    }


@app.get("/metrics")
async def metrics():
    per_path: dict[str, dict[str, float | int]] = {}

    for path, values in REQUEST_METRICS["by_path"].items():
        count = values["count"]
        total_duration_ms = values["total_duration_ms"]
        average_ms = (total_duration_ms / count) if count else 0.0
        per_path[path] = {
            "count": count,
            "errors": values["errors"],
            "avg_duration_ms": round(average_ms, 2),
        }

    return {
        "requests_total": REQUEST_METRICS["requests_total"],
        "errors_total": REQUEST_METRICS["errors_total"],
        "paths": per_path,
    }


@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
