import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import "./App.css";
import CvUpload from "./CvUpload";
import Notebook, { SaveButton } from "./Notebook";

const API_BASE_URL = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 300_000;

// نفس الحدود الموجودة بالـ backend
const MAX_CV = 3500;
const MAX_JOB = 2500;
const MAX_QUESTION = 1000;

type TaskType = "match" | "interview" | "advice";

interface CareerResponse {
  thread_id: string;
  task_type: string;
  workflow_status: string;
  final_response: string;
  tools_used: string[];
  agent_steps: number;
  history_count: number;
  error: string;
  execution_time: number;
}

interface ProgressStep {
  id: number;
  label: string;
  status: "running" | "done" | "error";
  tool?: string;
}

interface ProgressEvent {
  kind: string;
  message?: string;
  tool?: string;
  step?: number;
}

const TASKS: { id: TaskType; title: string; description: string }[] = [
  {
    id: "match",
    title: "CV ↔ Job Match",
    description: "Compare your CV with a job posting",
  },
  {
    id: "interview",
    title: "Interview Prep",
    description: "Get questions and tips for a job",
  },
  {
    id: "advice",
    title: "Career Advice",
    description: "Ask a career question or save a note",
  },
];

const TOOL_LABELS: Record<string, string> = {
  parse_cv: "Parse CV",
  match_job: "Match Job",
  search_tips: "Search Tips (RAG)",
  generate_interview_questions: "Interview Questions",
  save_notes: "Save Notes",
};

function formatStatus(status?: string): string {
  if (!status) return "Unknown";

  const labels: Record<string, string> = {
    completed: "Completed",
    completed_with_warnings: "Completed with Warnings",
    failed: "Failed",
    backend_failed: "Backend Failed",
    input_invalid: "Invalid Input",
  };

  return labels[status] ?? status.replace(/_/g, " ");
}

// يحوّل نص الـ Markdown البسيط (## عناوين و - نقاط) لعناصر HTML
function renderResponse(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let listItems: string[] = [];

  const flushList = (key: string) => {
    if (listItems.length > 0) {
      nodes.push(
        <ul key={key}>
          {listItems.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  text.split("\n").forEach((rawLine, index) => {
    const line = rawLine.trim();

    if (!line) {
      flushList(`ul-${index}`);
      return;
    }

    if (line.startsWith("## ")) {
      flushList(`ul-${index}`);
      nodes.push(<h3 key={`h-${index}`}>{line.slice(3)}</h3>);
      return;
    }

    if (line === "---") {
      flushList(`ul-${index}`);
      nodes.push(<hr key={`hr-${index}`} />);
      return;
    }

    if (line.startsWith("- ")) {
      listItems.push(line.slice(2));
      return;
    }

    if (/^\d+\.\s/.test(line)) {
      listItems.push(line.replace(/^\d+\.\s+/, ""));
      return;
    }

    flushList(`ul-${index}`);
    nodes.push(<p key={`p-${index}`}>{line}</p>);
  });

  flushList("ul-end");
  return nodes;
}

interface FieldProps {
  label: string;
  value: string;
  max: number;
  placeholder: string;
  disabled: boolean;
  onChange: (value: string) => void;
}

function Field({
  label,
  value,
  max,
  placeholder,
  disabled,
  onChange,
}: FieldProps) {
  return (
    <div className="field">
      <div className="field-header">
        <label>{label}</label>
        <span className="char-count">
          {value.length}/{max}
        </span>
      </div>
      <textarea
        dir="auto"
        rows={6}
        value={value}
        maxLength={max}
        placeholder={placeholder}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

function App() {
  const [task, setTask] = useState<TaskType>("match");
  const [cv, setCv] = useState("");
  const [job, setJob] = useState("");
  const [question, setQuestion] = useState("");

  const [threadId, setThreadId] = useState<string | null>(null);
  const [result, setResult] = useState<CareerResponse | null>(null);
  const [steps, setSteps] = useState<ProgressStep[]>([]);
  const [streamText, setStreamText] = useState("");
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [notebookVersion, setNotebookVersion] = useState(0);
  const [apiStatus, setApiStatus] = useState("Checking API...");

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Backend is not healthy");
        }
        setApiStatus("Backend connected");
      })
      .catch(() => {
        setApiStatus("Backend unavailable");
      });
  }, []);

  // عدّاد الثواني أثناء الانتظار
  useEffect(() => {
    if (!loading) return;

    const id = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [loading]);

  // خطوة جديدة: الخطوات اللي كانت "جارية" بتصير "منتهية"
  const addStep = (
    label: string,
    status: "running" | "error" = "running",
    tool?: string
  ) => {
    setSteps((prev) => [
      ...prev.map((s) =>
        s.status === "running" ? { ...s, status: "done" as const } : s
      ),
      { id: prev.length, label, status, tool },
    ]);
  };

  const markToolDone = (tool?: string) => {
    setSteps((prev) =>
      prev.map((s) =>
        s.tool === tool && s.status === "running"
          ? { ...s, status: "done" as const }
          : s
      )
    );
  };

  const finishAllSteps = () => {
    setSteps((prev) =>
      prev.map((s) =>
        s.status === "running" ? { ...s, status: "done" as const } : s
      )
    );
  };

  const handleProgress = (event: ProgressEvent) => {
    if (event.kind === "tool_done") {
      markToolDone(event.tool);
      return;
    }

    if (event.kind === "tool") {
      const name = event.tool ? TOOL_LABELS[event.tool] ?? event.tool : "tool";
      addStep(`Running tool: ${name}`, "running", event.tool);
      return;
    }

    if (event.kind === "failed") {
      addStep(event.message ?? "Failed", "error");
      return;
    }

    if (event.message) {
      addStep(event.message);
    }
  };

  const validate = (): string => {
    if (task === "match" && (!cv.trim() || !job.trim())) {
      return "Match analysis needs both your CV and the job posting.";
    }
    if (task === "interview" && !job.trim()) {
      return "Interview preparation needs the job posting.";
    }
    if (task === "advice" && !question.trim()) {
      return "Please write your question.";
    }
    return "";
  };

  const submit = async () => {
    const validationError = validate();

    if (validationError) {
      setError(validationError);
      return;
    }

    setError("");
    setResult(null);
    setSteps([]);
    setStreamText("");
    setElapsed(0);
    setLoading(true);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    let finalData: CareerResponse | null = null;

    const handleBlock = (block: string) => {
      let eventName = "message";
      let dataText = "";

      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataText += line.slice(5).trim();
        }
      }

      if (!dataText) return;

      try {
        const data = JSON.parse(dataText);

        if (eventName === "progress") {
          handleProgress(data as ProgressEvent);
        } else if (eventName === "token") {
          setStreamText((prev) => prev + (data.text ?? ""));
        } else if (eventName === "done") {
          finalData = data as CareerResponse;
        }
      } catch {
        // تجاهل أي حدث غير مفهوم
      }
    };

    try {
      const response = await fetch(`${API_BASE_URL}/career/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          task_type: task,
          cv_text: cv,
          job_text: job,
          user_question: question,
          thread_id: threadId,
        }),
      });

      if (!response.ok) {
        let message = "Invalid request. Check the field lengths.";

        try {
          const data = await response.json();
          if (typeof data.detail === "string") {
            message = data.detail;
          }
        } catch {
          // نبقي الرسالة الافتراضية
        }

        throw new Error(message);
      }

      if (!response.body) {
        throw new Error("The server did not send a stream.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";

        for (const block of blocks) {
          handleBlock(block);
        }
      }

      if (buffer.trim()) {
        handleBlock(buffer);
      }

      const finished = finalData as CareerResponse | null;

      if (!finished) {
        throw new Error("The connection closed before the result arrived.");
      }

      finishAllSteps();
      setResult(finished);
      setThreadId(finished.thread_id ?? threadId);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setError("The request took too long. Please try again.");
      } else {
        setError(
          err instanceof Error
            ? err.message
            : "An unexpected error occurred."
        );
      }
    } finally {
      clearTimeout(timer);
      setStreamText("");
      setLoading(false);
    }
  };

  const newSession = () => {
    setThreadId(null);
    setResult(null);
    setSteps([]);
    setCv("");
    setJob("");
    setQuestion("");
    setError("");
  };

  const copyResponse = async () => {
    try {
      await navigator.clipboard.writeText(result?.final_response ?? "");
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not copy the text.");
    }
  };

  const failed =
    !!result &&
    (["failed", "backend_failed", "input_invalid"].includes(
      result.workflow_status
    ) ||
      !!result.error);

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Career Assistant</h1>
          <p>CV analysis, job matching and interview preparation</p>
        </div>

        <div
          className={`api-status ${
            apiStatus === "Backend connected" ? "connected" : "offline"
          }`}
        >
          <span className="status-dot" />
          {apiStatus}
        </div>
      </header>

      <main className="container">
        <section className="card input-card">
          <h2>What do you need?</h2>

          <div className="task-tabs">
            {TASKS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`task-tab ${task === item.id ? "active" : ""}`}
                onClick={() => {
                  setTask(item.id);
                  setError("");
                }}
                disabled={loading}
              >
                <strong>{item.title}</strong>
                <span>{item.description}</span>
              </button>
            ))}
          </div>

          {(task === "match" || task === "interview") && (
            <Field
              label={task === "interview" ? "Your CV (optional)" : "Your CV"}
              value={cv}
              max={MAX_CV}
              placeholder="Paste your CV text here..."
              disabled={loading}
              onChange={setCv}
            />
          )}

          {(task === "match" || task === "interview") && (
            <CvUpload disabled={loading} onExtracted={setCv} />
          )}

          {(task === "match" || task === "interview") && (
            <Field
              label="Job Posting"
              value={job}
              max={MAX_JOB}
              placeholder="Paste the job posting here..."
              disabled={loading}
              onChange={setJob}
            />
          )}

          {task === "advice" && (
            <Field
              label="Your Question"
              value={question}
              max={MAX_QUESTION}
              placeholder="Example: How should I answer 'tell me about yourself'?"
              disabled={loading}
              onChange={setQuestion}
            />
          )}

          <div className="input-row">
            <button
              className="primary-button"
              onClick={() => void submit()}
              disabled={loading}
            >
              {loading ? "Working..." : "Run"}
            </button>

            {threadId && (
              <button
                className="secondary-button"
                onClick={newSession}
                disabled={loading}
              >
                New Session
              </button>
            )}
          </div>

          {threadId && (
            <p className="section-description">
              Session active
              {result ? ` · ${result.history_count} request(s) in memory` : ""}
            </p>
          )}

          {error && (
            <div className="error-box" role="alert">
              <strong>Error</strong>
              <span>{error}</span>
            </div>
          )}
        </section>

        {(loading || steps.length > 0) && (
          <section className="card progress-card">
            <div className="section-header">
              <h2>Workflow Progress</h2>
              {loading && (
                <span className="elapsed">
                  <span className="spinner small" /> {elapsed}s
                </span>
              )}
            </div>

            {loading && (
              <p className="section-description">
                The assistant calls the model several times, so it can
                take one to three minutes on a slow connection. Each
                step appears below as it happens.
              </p>
            )}

            <ol className="progress-list">
              {steps.map((step) => (
                <li
                  key={step.id}
                  className={`progress-step ${step.status}`}
                >
                  <span className="step-icon">
                    {step.status === "running" && (
                      <span className="spinner small" />
                    )}
                    {step.status === "done" && "✓"}
                    {step.status === "error" && "✕"}
                  </span>
                  <span>{step.label}</span>
                </li>
              ))}
            </ol>
          </section>
        )}

        {loading && streamText && (
          <section className="card">
            <div className="section-header">
              <h2>Result (writing...)</h2>
            </div>

            <div className="response-body" dir="auto">
              {renderResponse(streamText)}
              <span className="cursor" />
            </div>
          </section>
        )}

        {result && (
          <>
            <section className="status-grid">
              <div className="card status-card">
                <span className="label">Status</span>
                <strong>{formatStatus(result.workflow_status)}</strong>
              </div>

              <div className="card status-card">
                <span className="label">Execution Time</span>
                <strong>{result.execution_time}s</strong>
              </div>

              <div className="card status-card">
                <span className="label">Agent Steps</span>
                <strong>{result.agent_steps}</strong>
              </div>

              <div className="card status-card">
                <span className="label">Session Requests</span>
                <strong>{result.history_count}</strong>
              </div>
            </section>

            {result.tools_used.length > 0 && (
              <section className="card">
                <h2>Tools Used</h2>
                <div className="tool-tags">
                  {result.tools_used.map((name) => (
                    <span key={name}>{TOOL_LABELS[name] ?? name}</span>
                  ))}
                </div>
              </section>
            )}

            {failed ? (
              <section className="card error-card">
                <h2>Request Failed</h2>
                <div className="error-box" dir="auto">
                  {result.error || formatStatus(result.workflow_status)}
                </div>
              </section>
            ) : (
              <section className="card">
                <div className="section-header">
                  <h2>Result</h2>
                  <button
                    className="secondary-button"
                    onClick={() => void copyResponse()}
                  >
                    {copied ? "Copied ✓" : "Copy"}
                  </button>
                </div>

                <div className="response-body" dir="auto">
                  {renderResponse(result.final_response)}
                </div>

                {result.task_type === "match" && (
                  <SaveButton
                    finalResponse={result.final_response}
                    jobText={job}
                    onSaved={() => setNotebookVersion((v) => v + 1)}
                  />
                )}
              </section>
            )}
          </>
        )}
        <Notebook refreshKey={notebookVersion} />
      </main>
    </div>
  );
}

export default App;
