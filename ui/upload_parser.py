from __future__ import annotations

import csv
import io
import json
from pathlib import PurePosixPath

# Keep uploads bounded so prompts stay reasonable for the LLM.
DEFAULT_MAX_CHARS = 50_000


def _decode_text(data: bytes) -> str:
    """Decode bytes as UTF-8 with replacement for invalid sequences."""
    return data.decode("utf-8", errors="replace")


def parse_upload(
    filename: str,
    data: bytes,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> tuple[str, str]:
    """Read uploaded file bytes into a text excerpt for the agent pipeline.

    Args:
        filename: Original file name (used for extension detection).
        data: Raw file contents.
        max_chars: Truncate longer text and append a notice.

    Returns:
        (kind, text) where kind is a short label like "text", "csv", "json", or "binary".
    """
    if not data:
        return "empty", "(empty file)"

    suffix = PurePosixPath(filename or "").suffix.lower()

    if suffix in {".txt", ".md", ".markdown", ".log", ".yaml", ".yml"}:
        text = _decode_text(data)
        return "text", _truncate(text, max_chars)

    if suffix == ".csv":
        text = _csv_preview(data, max_rows=30)
        return "csv", _truncate(text, max_chars)

    if suffix == ".json":
        text = _json_pretty(data)
        return "json", _truncate(text, max_chars)

    if suffix in {".html", ".htm", ".xml"}:
        text = _decode_text(data)
        return "markup", _truncate(text, max_chars)

    # Heuristic: try UTF-8 for unknown extensions
    try:
        text = data.decode("utf-8")
        if "\x00" in text:
            return "binary", _binary_notice(filename, len(data))
        printable_ratio = sum(c.isprintable() or c in "\n\r\t" for c in text) / max(
            len(text), 1
        )
        if printable_ratio < 0.85:
            return "binary", _binary_notice(filename, len(data))
        return "text", _truncate(text, max_chars)
    except Exception:
        return "binary", _binary_notice(filename, len(data))


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    notice = f"\n\n[Truncated after {max_chars} characters; upload was longer.]"
    return text[:max_chars] + notice


def _csv_preview(data: bytes, *, max_rows: int) -> str:
    raw = _decode_text(data)
    reader = csv.reader(io.StringIO(raw))
    rows: list[list[str]] = []
    for i, row in enumerate(reader):
        if i >= max_rows:
            rows.append([f"... ({max_rows} rows max in preview)"])
            break
        rows.append(row)
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    for row in rows:
        w.writerow(row)
    return out.getvalue()


def _json_pretty(data: bytes) -> str:
    text = _decode_text(data)
    try:
        obj = json.loads(text)
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return text


def _binary_notice(filename: str, size: int) -> str:
    return (
        f"Binary or non-text file `{filename or 'upload'}` ({size} bytes) "
        "could not be inlined as text. Try CSV, JSON, or plain text."
    )


def build_prompt_with_upload(user_task: str, upload_label: str, upload_text: str) -> str:
    """Combine user task with uploaded content for the first HumanMessage."""
    task = user_task.strip() or "Use the uploaded data as context."
    if not upload_text.strip():
        return task
    return (
        f"{task}\n\n---\n**Uploaded file:** {upload_label}\n```\n{upload_text}\n```"
    )
