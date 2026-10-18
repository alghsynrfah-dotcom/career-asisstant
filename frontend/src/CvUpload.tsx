import { useRef, useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000";
const MAX_BYTES = 5 * 1024 * 1024;

interface CvUploadProps {
  disabled: boolean;
  onExtracted: (text: string) => void;
}

export default function CvUpload({ disabled, onExtracted }: CvUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);

  const fail = (text: string) => {
    setIsError(true);
    setMessage(text);
  };

  const handleFile = async (file: File) => {
    setMessage("");
    setIsError(false);

    if (!/\.(pdf|docx|txt)$/i.test(file.name)) {
      fail("Only PDF, Word (.docx) and text (.txt) files are supported.");
      return;
    }

    if (file.size > MAX_BYTES) {
      fail("The file is larger than 5 MB.");
      return;
    }

    setBusy(true);

    try {
      const form = new FormData();
      form.append("file", file);

      const response = await fetch(`${API_BASE_URL}/career/extract-cv`, {
        method: "POST",
        body: form,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Could not read the file."
        );
      }

      onExtracted(data.text);
      setMessage(
        `Text extracted from "${file.name}" (${data.characters} characters` +
          `${data.truncated ? ", shortened to fit the limit" : ""}). ` +
          "Please review it before running."
      );
    } catch (err) {
      fail(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);

      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  };

  return (
    <div className="cv-upload">
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];

          if (file) {
            void handleFile(file);
          }
        }}
      />

      <button
        type="button"
        className="secondary-button"
        disabled={disabled || busy}
        onClick={() => inputRef.current?.click()}
      >
        {busy ? "Reading file..." : "Upload CV (PDF / Word)"}
      </button>

      <span className={isError ? "upload-error" : "section-description"}>
        {message ||
          "Or paste the text above. The file is read in memory and never stored."}
      </span>
    </div>
  );
}
