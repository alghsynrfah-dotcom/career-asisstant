import time
import uuid
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.graph.graph import graph


app = FastAPI(
    title="Career Assistant API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CareerRequest(BaseModel):
    task_type: Literal["match", "interview", "advice"]
    cv_text: str = Field("", max_length=3500)
    job_text: str = Field("", max_length=2500)
    user_question: str = Field("", max_length=1000)
    thread_id: str | None = None


def build_response(state: dict, thread_id: str, execution_time: float) -> dict:
    return {
        "thread_id": thread_id,
        "task_type": state.get("task_type", ""),
        "workflow_status": state.get("workflow_status", ""),
        "final_response": state.get("final_response", ""),
        "tools_used": state.get("tools_used", []),
        "agent_steps": state.get("agent_steps", 0),
        "history_count": len(state.get("history", [])),
        "error": state.get("error", ""),
        "execution_time": round(execution_time, 3),
    }


def error_response(thread_id: str, exc: Exception, execution_time: float) -> dict:
    print(f"[API ERROR] {type(exc).__name__}: {exc}", flush=True)

    return {
        "thread_id": thread_id,
        "task_type": "",
        "workflow_status": "backend_failed",
        "final_response": "",
        "tools_used": [],
        "agent_steps": 0,
        "history_count": 0,
        "error": f"{type(exc).__name__}: {exc}",
        "execution_time": round(execution_time, 3),
    }


@app.get("/")
def root():
    return {"message": "Career Assistant API is running."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/career/analyze")
def analyze(request: CareerRequest):
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 15,
    }

    # منرسل بس الحقول المعبّاة، حتى لو المستخدم ما بعت CV بطلب جديد
    # بنفس الجلسة، يبقى الـ CV القديم محفوظ بالـ state.
    state_input = {"task_type": request.task_type}

    if request.cv_text.strip():
        state_input["cv_text"] = request.cv_text
    if request.job_text.strip():
        state_input["job_text"] = request.job_text
    if request.user_question.strip():
        state_input["user_question"] = request.user_question

    start_time = time.perf_counter()

    try:
        print(f"[CAREER] thread {thread_id}, task {request.task_type}", flush=True)

        graph.invoke(state_input, config=config)

        state = dict(graph.get_state(config).values)

        return build_response(
            state, thread_id, time.perf_counter() - start_time
        )

    except Exception as exc:
        return error_response(
            thread_id, exc, time.perf_counter() - start_time
        )


@app.get("/career/{thread_id}")
def get_session(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}

    try:
        state = dict(graph.get_state(config).values)

        if not state:
            raise HTTPException(status_code=404, detail="Session not found.")

        return build_response(state, thread_id, 0)

    except HTTPException:
        raise

    except Exception as exc:
        return error_response(thread_id, exc, 0)

# ---------------------------------------------------------------------------
# Streaming: نفس الـ workflow، بس كل خطوة بتنبعت للمتصفح لما تخلص
# (Server-Sent Events)
# ---------------------------------------------------------------------------
import json
from fastapi.responses import StreamingResponse


def sse(event: str, data: dict) -> str:
    """Format one Server-Sent Event."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


@app.post("/career/stream")
def analyze_stream(request: CareerRequest):
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 15,
    }

    state_input = {"task_type": request.task_type}

    if request.cv_text.strip():
        state_input["cv_text"] = request.cv_text
    if request.job_text.strip():
        state_input["job_text"] = request.job_text
    if request.user_question.strip():
        state_input["user_question"] = request.user_question

    node_messages = {
        "validate_input": (
            "validated",
            f"Request validated and routed to the '{request.task_type}' flow",
        ),
        "match_node": ("agent_done", "Analysis finished"),
        "interview_node": ("agent_done", "Interview questions prepared"),
        "advice_node": ("agent_done", "Answer prepared"),
        "finalize": ("finalized", "Final answer reviewed"),
        "failure": ("failed", "The request could not be completed"),
    }

    def event_stream():
        start_time = time.perf_counter()

        try:
            yield sse(
                "progress",
                {"kind": "start", "message": "Request received"},
            )

            # "updates": حدث عند انتهاء كل node. "custom": أحداث الـ agent.
            for mode, chunk in graph.stream(
                state_input,
                config=config,
                stream_mode=["updates", "custom"],
            ):
                if mode == "custom":
                    if chunk.get("kind") == "token":
                        yield sse("token", chunk)
                    else:
                        yield sse("progress", chunk)

                elif mode == "updates":
                    for node in chunk:
                        info = node_messages.get(node)

                        if info:
                            yield sse(
                                "progress",
                                {"kind": info[0], "message": info[1]},
                            )

            state = dict(graph.get_state(config).values)

            yield sse(
                "done",
                build_response(
                    state, thread_id, time.perf_counter() - start_time
                ),
            )

        except Exception as exc:
            yield sse(
                "done",
                error_response(
                    thread_id, exc, time.perf_counter() - start_time
                ),
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Notebook: المستخدم بيحفظ بإرادتو الفجوات واقتراحات التحسين بالـ RAG
# ---------------------------------------------------------------------------
from backend.services.rag_service import (
    save_user_entry,
    list_user_entries,
    delete_user_entry,
)


class NotebookRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    text: str = Field(..., min_length=1, max_length=3000)


@app.post("/notebook")
def notebook_save(request: NotebookRequest):
    try:
        return save_user_entry(request.title, request.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        print(f"[NOTEBOOK ERROR] {type(exc).__name__}: {exc}", flush=True)
        raise HTTPException(status_code=500, detail="Could not save the entry.")


@app.get("/notebook")
def notebook_list():
    try:
        return {"entries": list_user_entries()}
    except Exception as exc:
        print(f"[NOTEBOOK ERROR] {type(exc).__name__}: {exc}", flush=True)
        raise HTTPException(status_code=500, detail="Could not load the notebook.")


@app.delete("/notebook/{tip_id}")
def notebook_delete(tip_id: str):
    if not delete_user_entry(tip_id):
        raise HTTPException(status_code=404, detail="Entry not found.")
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# رفع الـ CV: بنطلّع النص بس. الملف ما بينحفظ وما بيدخل بالـ graph.
# ---------------------------------------------------------------------------
from fastapi import File, UploadFile
from fastapi.concurrency import run_in_threadpool

from backend.services.cv_extract import MAX_UPLOAD_BYTES, extract_cv_text


@app.post("/career/extract-cv")
async def extract_cv(file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD_BYTES + 1)

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="The file is larger than 5 MB.",
        )

    try:
        return await run_in_threadpool(
            extract_cv_text, file.filename or "", data
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        print(f"[CV UPLOAD ERROR] {type(exc).__name__}", flush=True)
        raise HTTPException(status_code=500, detail="Could not read the file.")
