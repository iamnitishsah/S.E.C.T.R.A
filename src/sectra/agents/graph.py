"""The research graph: one entry point for numeric, narrative and hybrid questions.

    python -m sectra.agents.graph "How fast did Nvidia's revenue grow in fiscal 2025, and what drove it?"
    python -m sectra.agents.graph "..." --show-sql --show-passages
    python -m sectra.agents.graph --diagram          # print the graph as a Mermaid diagram

LangGraph in three ideas, as used here:
  State   one dict shared by all nodes (ResearchState). A node returns only the keys it changes and
          LangGraph merges them in. `trace` has a reducer (operator.add), so each node's list is
          appended instead of replacing the previous one.
  Nodes   plain functions from nodes.py: router, sql, text, writer, refuse.
  Edges   fixed (text -> writer) or conditional: a function reads the state and names the next node.

    START -> router -> refuse -> END                 the corpus cannot answer
             router -> sql -> writer -> END          numeric question
             router -> text -> writer -> END         narrative question
             router -> sql -> text -> writer -> END  hybrid question
"""

from __future__ import annotations

import argparse
import json
import operator
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from sectra.agents import nodes
from sectra.agents.nodes import Deps

ROOT = Path(__file__).resolve().parents[3]


class ResearchState(TypedDict, total=False):
    question: str
    route: Any                                   # router.Route
    sql: Any                                     # analyst.agent.SQLAnswer (query, rows, sources), or missing
    passages: list[dict]                         # numbered in the order the writer sees them
    answer: str
    not_found: bool
    reason: str
    checks: dict
    model: str
    usage: dict                                  # tokens and LLM latency, summed over all nodes
    trace: Annotated[list[str], operator.add]    # one line per step; appended, never overwritten


def after_router(state: ResearchState) -> str:
    r = state["route"]
    if r.refused:
        return "refuse"
    return "text" if r.route == "text" else "sql"


def after_sql(state: ResearchState) -> str:
    return "text" if state["route"].route == "both" else "writer"


def build_graph(deps: Deps):
    g = StateGraph(ResearchState)
    for name in ("router", "refuse", "sql", "text", "writer"):
        g.add_node(name, partial(getattr(nodes, f"{name}_node"), deps=deps))
    g.add_edge(START, "router")
    g.add_conditional_edges("router", after_router, {"refuse": "refuse", "sql": "sql", "text": "text"})
    g.add_conditional_edges("sql", after_sql, {"text": "text", "writer": "writer"})
    g.add_edge("text", "writer")
    g.add_edge("writer", END)
    g.add_edge("refuse", END)
    return g.compile()


def make_deps(backend: str | None = None, retriever_name: str | None = None) -> Deps:  # pragma: no cover - needs services
    import yaml
    from dotenv import load_dotenv

    from sectra.agents.router import load_catalog
    from sectra.analyst.tools import get_schema
    from sectra.analyst.tools import load_config as load_sql_config
    from sectra.llm.base import get_llm
    from sectra.llm.base import load_config as load_llm_config
    from sectra.retrieval.factory import get_retriever
    from sectra.storage.mysql import get_engine, get_reader_engine

    load_dotenv(ROOT / ".env")
    rcfg = yaml.safe_load(open(ROOT / "configs" / "retrieval.yaml"))
    variant = retriever_name or rcfg["answering"]["retriever"]
    gen = load_llm_config().get("generation", {})
    reader = get_reader_engine()
    return Deps(llm=get_llm(backend), retriever=get_retriever(variant), engine=reader,
                catalog=load_catalog(get_engine()), sql_cfg=load_sql_config(), schema=get_schema(reader),
                top_k=rcfg["vector_store"].get("top_k", 5), min_score=rcfg["answering"]["min_score"].get(variant, 0.0),
                temperature=gen.get("temperature", 0.0), max_tokens=gen.get("max_tokens", 2000))


def log_run(state: dict, backend: str) -> None:
    path = ROOT / "data" / "logs" / "graph.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    r, sql = state["route"], state.get("sql")
    record = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "question": state["question"],
              "backend": backend, "route": r.route, "refused": r.refused, "tickers": r.tickers,
              "fiscal_years": r.fiscal_years, "sql": sql.sql if sql else "", "n_rows": len(sql.rows) if sql else 0,
              "chunk_ids": [p["chunk_id"] for p in state.get("passages") or []], "answer": state.get("answer", ""),
              "not_found": state.get("not_found", False), "reason": state.get("reason", ""),
              "checks": state.get("checks", {}), "trace": state.get("trace", []), "usage": state.get("usage", {})}
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def print_result(state: dict, show_sql: bool, show_passages: bool) -> None:
    from sectra.analyst.tools import QueryResult, format_rows
    print("\n" + "=" * 80)
    print(state.get("answer", ""))
    if state.get("not_found"):
        print(f"\n(reason: {state.get('reason', '')})")
    sql, passages, checks = state.get("sql"), state.get("passages") or [], state.get("checks") or {}
    if sql is not None and sql.rows:
        print("\n[T] " + format_rows(QueryResult(True, sql.sql, sql.columns, sql.rows), max_rows=12).replace("\n", "\n    "))
        if sql.sources:
            print(f"    source filings: {', '.join(sql.sources)}")
    if sql is not None and show_sql and sql.sql:
        print(f"\n--- SQL\n{sql.sql}")
    if passages:
        print("\nPassages:")
        cited = checks.get("cited_passages", [])
        for n, p in enumerate(passages, start=1):
            print(f" {'*' if n in cited else ' '}[{n}] {p['header']}  (score {p['score']:.3f})")
            print(f"       {p['chunk_id']}  {p.get('source_url', '')}")
            if show_passages:
                print("       " + p["text"][:500].replace("\n", "\n       "))
    if checks.get("invalid_citations"):
        print(f"\n!! citations to passages that were not shown: {checks['invalid_citations']}")
    if checks.get("uncited_sentences"):
        print(f"\n!! {len(checks['uncited_sentences'])} sentence(s) without a source:")
        for s in checks["uncited_sentences"][:3]:
            print(f"   - {s[:120]}")
    if checks.get("unsupported_numbers"):
        print(f"\n!! numbers that are in neither the table nor the passages: {', '.join(checks['unsupported_numbers'])}")
    if checks.get("truncated"):
        print("\n!! the answer was cut off at the token limit")
    print("\nSteps:")
    for step in state.get("trace", []):
        print(f"  - {step}")
    u = state.get("usage") or {}
    print(f"\n[{state.get('model', '')} | {u.get('input_tokens', 0)} in / {u.get('output_tokens', 0)} out tokens "
          f"| {u.get('latency_s', 0)}s in LLM calls]")


def main() -> None:  # pragma: no cover - needs services
    p = argparse.ArgumentParser(description="Ask a numeric, narrative or hybrid question.")
    p.add_argument("question", nargs="?")
    p.add_argument("--backend", help="LLM backend from configs/llm.yaml")
    p.add_argument("--retriever", help="retrieval variant (default: answering.retriever)")
    p.add_argument("--show-sql", action="store_true")
    p.add_argument("--show-passages", action="store_true")
    p.add_argument("--diagram", action="store_true", help="print the graph as Mermaid and exit")
    args = p.parse_args()
    if args.diagram:
        print(build_graph(Deps(None, None, None, None, {}, "")).get_graph().draw_mermaid())
        return
    if not args.question:
        p.error("a question is required")
    deps = make_deps(args.backend, args.retriever)
    print(f"[backend: {deps.llm.name} / {deps.llm.model}]")
    state = build_graph(deps).invoke({"question": args.question})
    print_result(state, args.show_sql, args.show_passages)
    log_run(state, deps.llm.name)


if __name__ == "__main__":
    main()