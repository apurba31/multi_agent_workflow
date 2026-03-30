from __future__ import annotations

import json

from ui.upload_parser import (
    DEFAULT_MAX_CHARS,
    build_prompt_with_upload,
    parse_upload,
)


class TestParseUpload:
    def test_empty(self):
        kind, text = parse_upload("x.txt", b"")
        assert kind == "empty"
        assert "empty" in text.lower()

    def test_txt(self):
        kind, text = parse_upload("notes.txt", b"hello world")
        assert kind == "text"
        assert text == "hello world"

    def test_md(self):
        kind, text = parse_upload("README.md", b"# Title\n")
        assert kind == "text"
        assert "# Title" in text

    def test_csv_preview(self):
        kind, text = parse_upload("data.csv", b"a,b\n1,2\n3,4\n")
        assert kind == "csv"
        assert "a,b" in text
        assert "1,2" in text

    def test_json_pretty(self):
        payload = {"x": 1, "y": [2, 3]}
        kind, text = parse_upload("cfg.json", json.dumps(payload).encode())
        assert kind == "json"
        assert '"x": 1' in text

    def test_json_invalid_falls_back_to_text(self):
        kind, text = parse_upload("bad.json", b"not json {")
        assert kind == "json"
        assert "not json" in text

    def test_truncation(self):
        data = b"x" * (DEFAULT_MAX_CHARS + 1000)
        kind, text = parse_upload("big.txt", data)
        assert kind == "text"
        assert len(text) < len(data.decode())
        assert "Truncated" in text

    def test_binary_heuristic(self):
        kind, text = parse_upload("unknown.bin", b"\x00\x01\x02\xff")
        assert kind == "binary"
        assert "Binary" in text or "could not" in text

    def test_unknown_utf8_plain(self):
        kind, text = parse_upload("noext", b"plain ascii here\n")
        assert kind == "text"
        assert "plain ascii" in text


class TestBuildPromptWithUpload:
    def test_task_only(self):
        assert build_prompt_with_upload("Do X", "f.csv", "") == "Do X"

    def test_default_task_when_empty(self):
        out = build_prompt_with_upload("", "f.txt", "body")
        assert "Use the uploaded data" in out
        assert "body" in out

    def test_includes_upload_block(self):
        out = build_prompt_with_upload("Summarize", "data.csv", "a,b\n1")
        assert "Summarize" in out
        assert "data.csv" in out
        assert "```" in out
        assert "a,b" in out
