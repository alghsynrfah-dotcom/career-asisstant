# Career Assistant

An AI career assistant built with LangGraph, a single ReAct agent, MCP tools,
RAG (embeddings + pgvector), FastAPI and React.

It analyzes a CV (pasted or uploaded as PDF or Word) against a job posting,
prepares interview questions, answers career questions from a tips knowledge
base, and keeps a personal notebook of saved notes and skill gaps.

## Setup
1. Copy `.env.example` to `.env` and fill in your own values.
2. Create a PostgreSQL database named `career_assistant` with the `vector` extension.
3. Install the Python requirements, then run `python -m backend.services.seed_tips`.
4. Start the API: `python -m uvicorn backend.main:app --port 8000`
5. Start the UI: `cd frontend && npm install && npm run dev`

No secrets are stored in this repository.
