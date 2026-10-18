import io
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# مكتبات إضافية (pypdf) بتنحط بمجلد .pydeps بدون ما نلمس أي venv
_DEPS_DIR = Path(__file__).resolve().parents[2] / ".pydeps"
if _DEPS_DIR.is_dir() and str(_DEPS_DIR) not in sys.path:
    sys.path.append(str(_DEPS_DIR))

MAX_UPLOAD_BYTES = 5 * 1024 * 1024   # 5 MB
MAX_CV_CHARS = 3500                  # نفس حد الـ CV بالـ backend والواجهة
MAX_PDF_PAGES = 5
MAX_DOCX_XML_BYTES = 10 * 1024 * 1024

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _clean(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _read_pdf(data: bytes) -> str:
    if not data.startswith(b"%PDF"):
        raise ValueError("This file is not a valid PDF.")

    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError("PDF support is not installed on the server.")

    try:
        reader = PdfReader(io.BytesIO(data))

        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError("This PDF is password-protected.")

        parts = []
        for page in reader.pages[:MAX_PDF_PAGES]:
            parts.append(page.extract_text() or "")

        return "\n".join(parts)

    except ValueError:
        raise
    except Exception:
        raise ValueError("Could not read this PDF file.")


def _read_docx(data: bytes) -> str:
    if not data.startswith(b"PK"):
        raise ValueError(
            "This is not a .docx file. Old .doc files must be saved as .docx."
        )

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info = archive.getinfo("word/document.xml")

            if info.file_size > MAX_DOCX_XML_BYTES:
                raise ValueError("The Word file is too large to read.")

            xml_bytes = archive.read("word/document.xml")

    except (KeyError, zipfile.BadZipFile):
        raise ValueError("This file is not a valid Word (.docx) file.")

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        raise ValueError("Could not read this Word file.")

    paragraphs = []

    # الجداول بتنقرا كمان لأنو فقراتها جوا نفس الـ XML
    for paragraph in root.iter(f"{W_NS}p"):
        pieces = []

        for node in paragraph.iter():
            if node.tag == f"{W_NS}t" and node.text:
                pieces.append(node.text)
            elif node.tag == f"{W_NS}tab":
                pieces.append("\t")
            elif node.tag in (f"{W_NS}br", f"{W_NS}cr"):
                pieces.append("\n")

        paragraphs.append("".join(pieces))

    return "\n".join(paragraphs)


def _read_txt(data: bytes) -> str:
    if b"\x00" in data[:2000]:
        raise ValueError("This file is not a text file.")

    return data.decode("utf-8", errors="ignore")


def extract_cv_text(filename: str, data: bytes) -> dict:
    """يطلّع النص من PDF أو Word أو txt. الملف ما بينحفظ بأي مكان."""
    name = (filename or "").lower()

    if not data:
        raise ValueError("The file is empty.")

    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("The file is larger than 5 MB.")

    if name.endswith(".pdf"):
        raw = _read_pdf(data)
    elif name.endswith(".docx"):
        raw = _read_docx(data)
    elif name.endswith(".txt"):
        raw = _read_txt(data)
    else:
        raise ValueError(
            "Only PDF, Word (.docx) and text (.txt) files are supported."
        )

    text = _clean(raw)

    if not text:
        raise ValueError(
            "No text was found in the file. If it is a scanned PDF, "
            "paste the text manually."
        )

    original_length = len(text)
    truncated = original_length > MAX_CV_CHARS

    if truncated:
        text = text[:MAX_CV_CHARS]

    return {
        "text": text,
        "characters": len(text),
        "original_characters": original_length,
        "truncated": truncated,
    }
