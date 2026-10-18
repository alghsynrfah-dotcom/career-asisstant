import { useCallback, useEffect, useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000";

interface Entry {
  id: string;
  title: string;
  category: string;
  created_at: string;
  preview: string;
}

// بياخد بس قسمي Gaps و Suggested CV Improvements (مو السيرة الذاتية)
function extractSections(text: string): string {
  const wanted = ["gaps", "suggested cv improvements"];
  const out: string[] = [];
  let keep = false;

  for (const raw of text.split("\n")) {
    const line = raw.trim();

    if (line.startsWith("## ")) {
      const name = line.slice(3).trim();
      keep = wanted.includes(name.toLowerCase());

      if (keep) out.push(`${name}:`);
      continue;
    }

    if (line === "---") {
      keep = false;
      continue;
    }

    if (keep && line) out.push(line);
  }

  return out.join(" ");
}

interface SaveButtonProps {
  finalResponse: string;
  jobText: string;
  onSaved: () => void;
}

export function SaveButton({
  finalResponse,
  jobText,
  onSaved,
}: SaveButtonProps) {
  const [status, setStatus] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");

  const text = extractSections(finalResponse);

  if (!text) return null;

  const firstLine =
    jobText
      .split("\n")
      .map((line) => line.trim())
      .find((line) => line) ?? "job";

  const title = `Gaps for: ${firstLine.slice(0, 60)}`;

  const save = async () => {
    setStatus("saving");

    try {
      const response = await fetch(`${API_BASE_URL}/notebook`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, text: text.slice(0, 3000) }),
      });

      if (!response.ok) throw new Error("save failed");

      setStatus("saved");
      onSaved();
    } catch {
      setStatus("error");
    }
  };

  return (
    <div className="notebook-save">
      <button
        className="secondary-button"
        onClick={() => void save()}
        disabled={status === "saving" || status === "saved"}
      >
        {status === "saving" && "Saving..."}
        {status === "saved" && "Saved ✓"}
        {status === "error" && "Failed, try again"}
        {status === "idle" && "Save gaps to my notebook"}
      </button>
      <span className="section-description">
        Saves only the gaps and improvement tips, not your CV.
      </span>
    </div>
  );
}

interface NotebookProps {
  refreshKey: number;
}

export default function Notebook({ refreshKey }: NotebookProps) {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/notebook`);

      if (!response.ok) throw new Error("load failed");

      const data = await response.json();
      setEntries(data.entries ?? []);
      setError("");
    } catch {
      setError("Could not load the notebook.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  const remove = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/notebook/${id}`, {
        method: "DELETE",
      });

      if (!response.ok) throw new Error("delete failed");

      await load();
    } catch {
      setError("Could not delete the entry.");
    }
  };

  return (
    <section className="card">
      <div className="section-header">
        <div>
          <h2>My Notebook</h2>
          <p className="section-description">
            Notes and analyses you saved. The assistant searches them when
            you ask for advice.
          </p>
        </div>

        <button className="secondary-button" onClick={() => void load()}>
          Refresh
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {entries.length === 0 && !error && (
        <div className="empty-state">Nothing saved yet.</div>
      )}

      <div className="notebook-list">
        {entries.map((entry) => (
          <article className="notebook-entry" key={entry.id}>
            <div dir="auto">
              <strong>{entry.title}</strong>
              <p>{entry.preview}</p>
              <span className="section-description">
                {entry.category === "my_note" ? "Note" : "Analysis"} ·{" "}
                {new Date(entry.created_at).toLocaleString()}
              </span>
            </div>

            <button
              className="secondary-button"
              onClick={() => void remove(entry.id)}
            >
              Delete
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
