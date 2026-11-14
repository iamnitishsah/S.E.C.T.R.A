"""
Cut Item sections into retrieval chunks.

    python -m sectra.ingestion.chunker

Rules (why each exists):
  - Split on paragraph lines, never mid-sentence unless a paragraph is too long.
  - [TABLE] blocks stay whole; a table too big for one chunk is split by rows and
    every piece repeats the header row, so numbers never lose their column labels.
  - Consecutive chunks overlap by ~overlap_tokens of whole lines, so a fact that
    spans a boundary is still fully inside one chunk.
  - A heading never ends a chunk; it moves to the next one, with its content.
  - Each chunk gets a context header ("AMD 10-K FY2025 | Item 1A Risk Factors | <subheading>")
    that is embedded with it, so a chunk makes sense on its own.
  - chunk_id = <accession>_<item>_<seq>: stable across rebuilds (never auto-increment).
Only filings whose Items 1A and 7 both parsed "ok" are chunked.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Callable

ITEM_TITLES = {
    "1": "Business",
    "1A": "Risk Factors",
    "1C": "Cybersecurity",
    "3": "Legal Proceedings",
    "7": "Management's Discussion and Analysis",
    "7A": "Quantitative and Qualitative Disclosures About Market Risk",
}
ITEM_HEADING_RE = re.compile(r"(part\s+[ivx]+|item\s*\d)", re.I)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"\u201c])")

TokenCounter = Callable[[str], int]


# ------------------------------------------------------------------ blocks

def to_blocks(text: str) -> list[dict]:
    """Section text -> blocks: one per paragraph line, one per whole [TABLE]."""
    blocks, table = [], None
    for line in text.split("\n"):
        line = line.strip()
        if line == "[TABLE]":
            table = []
        elif line == "[/TABLE]":
            if table:
                blocks.append({"kind": "table", "rows": table})
            table = None
        elif table is not None:
            table.append(line)
        elif line:
            blocks.append({"kind": "heading" if is_heading(line) else "text", "text": line})
    if table:                                            # unterminated table: keep the rows
        blocks.append({"kind": "table", "rows": table})
    return blocks


def demote_lists(blocks: list[dict], max_run: int = 2) -> list[dict]:
    """Runs of 3+ consecutive short lines are a list (names, products), not headings.
    Left as headings they would never close a chunk and their content would be lost."""
    out, i = [], 0
    while i < len(blocks):
        j = i
        while j < len(blocks) and blocks[j]["kind"] == "heading":
            j += 1
        run = blocks[i:j]
        if len(run) > max_run:
            run = [{"kind": "text", "text": b["text"]} for b in run]
        out.extend(run or [blocks[i]])
        i = max(j, i + 1)
    return out


def is_heading(line: str) -> bool:
    """Short line that labels what follows: no sentence ending, not a bullet or lead-in."""
    words = line.split()
    return (
            0 < len(words) <= 20
            and not line.endswith((".", ";", ":", ","))
            and not line.startswith(("\u2022", "-", "\u2013", "("))
            and not line[0].isdigit()
    )


def block_text(b: dict) -> str:
    if b["kind"] == "table":
        return "[TABLE]\n" + "\n".join(b["rows"]) + "\n[/TABLE]"
    return b["text"]


# ----------------------------------------------------- oversize splitting

def split_oversize(b: dict, limit: int, count: TokenCounter) -> list[dict]:
    """Split one block that alone exceeds the limit."""
    if b["kind"] == "table":
        header, rows = b["rows"][0], b["rows"][1:]
        room = max(limit - count(block_text({"kind": "table", "rows": [header]})), 20)
        fitted = []
        for row in rows:                                 # a single row can be huge (a bio in a cell):
            if count(row) <= room:                       # cut it by words so every piece fits
                fitted.append(row)
                continue
            words, part = row.split(), []
            for w in words:
                if part and count(" ".join(part + [w])) > room:
                    fitted.append(" ".join(part))
                    part = []
                part.append(w)
            fitted.append(" ".join(part))
        rows = fitted
        pieces, cur = [], []
        for row in rows:
            trial = {"kind": "table", "rows": [header] + cur + [row]}
            if cur and count(block_text(trial)) > limit:
                pieces.append({"kind": "table", "rows": [header] + cur})
                cur = []
            cur.append(row)
        pieces.append({"kind": "table", "rows": [header] + cur})
        return pieces

    pieces, cur = [], ""
    for sent in SENTENCE_RE.split(b["text"]):
        if count(sent) > limit:                          # pathological sentence: cut by words
            words, part = sent.split(), []
            for w in words:
                if part and count(" ".join(part + [w])) > limit:
                    pieces.append({"kind": "text", "text": " ".join(part)})
                    part = []
                part.append(w)
            sent = " ".join(part)
        trial = f"{cur} {sent}".strip()
        if cur and count(trial) > limit:
            pieces.append({"kind": "text", "text": cur})
            trial = sent
        cur = trial
    if cur:
        pieces.append({"kind": "text", "text": cur})
    return pieces


# ---------------------------------------------------------------- packing

def chunk_section(text: str, meta: dict, count: TokenCounter,
                  target: int = 350, overlap: int = 50) -> list[dict]:
    """Pack blocks into chunks of ~target tokens with ~overlap tokens of carry-over."""
    blocks = []
    for b in demote_lists(to_blocks(text)):
        blocks.extend(split_oversize(b, target, count) if count(block_text(b)) > target else [b])
    sizes = [count(block_text(b)) for b in blocks]

    # cur holds (block, tokens, subheading in force at that block)
    chunks, cur, cur_tokens, subheading, carried = [], [], 0, "", 0

    def emit():
        nonlocal cur, cur_tokens, carried
        carry = []
        while cur and cur[-1][0]["kind"] == "heading":   # a heading never ends a chunk
            carry.insert(0, cur.pop())
        if cur and any(b["kind"] != "heading" for b, _, _ in cur):
            body = "\n".join(block_text(b) for b, _, _ in cur)
            sub = next(sh for b, _, sh in cur if b["kind"] != "heading")  # subheading of the content
            chunks.append({"subheading": sub, "body": body})
            tail, t = [], 0                              # overlap: whole text lines from the end
            for b, n, sh in reversed(cur):
                if b["kind"] != "text" or t + n > overlap:
                    break
                tail.insert(0, (b, n, sh))
                t += n
            cur = tail + carry
        else:
            cur = cur + carry
        cur_tokens = sum(n for _, n, _ in cur)
        carried = len(cur)

    for b, n in zip(blocks, sizes):
        if b["kind"] == "heading" and not ITEM_HEADING_RE.match(b["text"]):
            subheading = b["text"]
        if cur_tokens + n > target:
            if len(cur) > carried:                       # has new content: close the chunk
                emit()
            if cur_tokens + n > target:                  # overlap alone + this block too big:
                cur = [x for x in cur if x[0]["kind"] == "heading"]   # drop the overlap
                cur_tokens, carried = sum(x[1] for x in cur), len(cur)
        cur.append((b, n, subheading))
        cur_tokens += n
    if cur:
        emit()

    title = ITEM_TITLES.get(meta["item_code"], "")
    out = []
    for seq, c in enumerate(chunks):
        header = f"{meta['ticker']} {meta['form_type']} FY{meta['fiscal_year']} | Item {meta['item_code']} {title}"
        if c["subheading"] and c["subheading"].lower() not in (title.lower(), header.lower()):
            header += f" | {c['subheading'][:120]}"
        out.append({
            "chunk_id": f"{meta['accession_no']}_{meta['item_code']}_{seq:03d}",
            **meta,
            "item_title": title,
            "seq": seq,
            "subheading": c["subheading"],
            "header": header,
            "text": c["body"],
            "n_tokens": count(header + "\n" + c["body"]),
        })
    return out


# -------------------------------------------------------------------- main

def main() -> None:  # pragma: no cover - needs MySQL + tokenizer download
    import yaml
    from sqlalchemy import bindparam, text as sql
    from transformers import AutoTokenizer

    from sectra.storage.mysql import get_engine

    root = Path(__file__).resolve().parents[3]
    cfg = yaml.safe_load(open(root / "configs" / "retrieval.yaml"))
    items = [str(i) for i in cfg["index_items"]]
    ch = cfg["chunking"]

    tok = AutoTokenizer.from_pretrained(cfg["chunking"]["tokenizer"])
    tok.model_max_length = 1_000_000          # we only count tokens; silences the ">512" warning

    def count(s: str) -> int:
        return len(tok(s, add_special_tokens=False)["input_ids"])

    query = sql("""
                SELECT s.accession_no, s.item_code, s.text_path, f.fiscal_year, f.form_type,
                       f.primary_doc_url AS source_url, c.ticker, c.cik
                FROM filing_sections s
                         JOIN filings f ON f.accession_no = s.accession_no
                         JOIN companies c ON c.cik = f.cik
                WHERE s.item_code IN :items
                  AND s.accession_no IN (SELECT accession_no FROM filing_sections
                                         WHERE item_code IN ('1A', '7') AND quality = 'ok'
                                         GROUP BY accession_no HAVING COUNT(*) = 2)
                ORDER BY c.ticker, f.fiscal_year, s.item_code
                """).bindparams(bindparam("items", expanding=True))
    with get_engine().connect() as conn:
        sections = conn.execute(query, {"items": items}).mappings().all()

    out = root / "data" / "processed" / "chunks" / "chunks.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    per_item, sizes, n = Counter(), [], 0
    with open(out, "w", encoding="utf-8") as fh:
        for s in sections:
            meta = {k: s[k] for k in ("accession_no", "ticker", "cik", "fiscal_year",
                                      "form_type", "item_code", "source_url")}
            text = (root / s["text_path"]).read_text(encoding="utf-8")
            for c in chunk_section(text, meta, count, ch["target_tokens"], ch["overlap_tokens"]):
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
                per_item[c["item_code"]] += 1
                sizes.append(c["n_tokens"])
                n += 1

    over = sum(x > ch["max_tokens"] for x in sizes)
    print(f"{len(sections)} sections -> {n:,} chunks -> {out.relative_to(root)}")
    print("per item:", dict(sorted(per_item.items())))
    print(f"tokens/chunk: min {min(sizes)}, median {statistics.median(sizes):.0f}, "
          f"p95 {sorted(sizes)[int(len(sizes) * .95)]}, max {max(sizes)} | over {ch['max_tokens']}: {over}")


if __name__ == "__main__":
    main()