from __future__ import annotations

import sys
from pathlib import Path

# Allow `streamlit run ui/app.py` from repo root without editable install.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from graph.runner import stream_graph_run
from ui.upload_parser import build_prompt_with_upload, parse_upload


def main() -> None:
    st.set_page_config(
        page_title="Multi-Agent Workflow",
        page_icon="🤖",
        layout="wide",
    )
    st.title("Multi-Agent workflow")
    st.caption(
        "Orchestrator → research / browser / comms / code → reflection. "
        "Requires Ollama and dependencies (`pip install -e \".[dev,ui]\"`)."
    )

    with st.sidebar:
        st.header("Upload")
        uploaded = st.file_uploader(
            "Data file (text, CSV, JSON, Markdown…)",
            type=["txt", "md", "csv", "json", "log", "yaml", "yml", "html", "xml"],
        )
        upload_kind = ""
        upload_text = ""
        if uploaded is not None:
            raw = uploaded.getvalue()
            upload_kind, upload_text = parse_upload(uploaded.name, raw)
            st.success(f"Loaded as **{upload_kind}** ({len(raw):,} bytes)")
            with st.expander("Preview (parsed text)"):
                st.text(upload_text[:4000] + ("…" if len(upload_text) > 4000 else ""))

    col1, col2 = st.columns([2, 1])
    with col1:
        task = st.text_area(
            "Task / instructions",
            placeholder="e.g. Summarize the uploaded CSV and list top 3 rows by value.",
            height=120,
        )
    with col2:
        thread_id = st.text_input("Thread ID (optional, for resume)", value="")

    run_btn = st.button("Run pipeline", type="primary")

    if not run_btn:
        return

    full_task = build_prompt_with_upload(
        task,
        uploaded.name if uploaded else "(no file)",
        upload_text if uploaded else "",
    )

    steps: list[tuple[str, dict]] = []
    status = st.status("Running graph…", expanded=True)
    try:
        meta = {"upload_filename": uploaded.name if uploaded else None, "upload_kind": upload_kind}
        for node_name, out in stream_graph_run(
            full_task,
            thread_id=thread_id.strip() or None,
            metadata={k: v for k, v in meta.items() if v},
        ):
            steps.append((node_name, out))
            err = out.get("error")
            na = out.get("next_agent", "—")
            line = f"**{node_name}** → next=`{na}`"
            if err:
                line += f" | error: `{err}`"
            status.write(line)
        status.update(label="Run finished", state="complete")
    except Exception as exc:
        status.update(label="Run failed", state="error")
        st.error(str(exc))
        return

    st.subheader("Step timeline")
    for i, (node_name, out) in enumerate(steps, start=1):
        with st.expander(f"{i}. {node_name}", expanded=(node_name != "orchestrator")):
            if out.get("subtask"):
                st.markdown("**Subtask**")
                st.code(out["subtask"], language=None)
            if out.get("result") is not None:
                st.markdown("**Result**")
                st.markdown(str(out["result"]))
            if out.get("messages"):
                last = out["messages"][-1]
                content = getattr(last, "content", str(last))
                if content and (not out.get("result") or str(content) != str(out["result"])):
                    st.markdown("**Message**")
                    st.markdown(str(content)[:8000])
            if out.get("error"):
                st.warning(str(out["error"]))

    final = steps[-1][1] if steps else {}
    st.success("Done")
    st.markdown("### Final output")
    st.write(final.get("result", "No result produced."))


if __name__ == "__main__":
    main()
