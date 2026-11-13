"""Convert a 10-K .htm file into clean text, remembering where linked anchors sit.

Why not BeautifulSoup.get_text("\\n")? It breaks lines at *every* element, so a
heading built from styled <span>s ("RIS" + "K FACTORS") gets split in half.
Here only block elements (p, div, tr, ...) start a new line.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

BLOCK_TAGS = {
    "p", "div", "br", "tr", "li", "ul", "ol", "table", "h1", "h2", "h3", "h4", "h5", "h6",
    "section", "article", "center", "blockquote", "hr", "body", "dl", "dt", "dd",
}
SKIP_TAGS = {"script", "style", "head", "title", "ix:header"}
MARK_OPEN, MARK_CLOSE = "\ue000", "\ue001"           # private-use chars: never appear in filings
MARK_RE = re.compile(f"{MARK_OPEN}(.*?){MARK_CLOSE}")
WS_RE = re.compile(r"[ \t\r\f\v\u00a0\u2009\u200b]+")
DROP_CELLS = {"$", "%", ")", "(", ""}
BULLETS = {"•", "●", "◦", "▪", "-", "–", "—"}


@dataclass
class Document:
    text: str                                   # clean text; tables wrapped in [TABLE] ... [/TABLE]
    anchors: dict[str, int]                     # link target id -> character offset in text
    links: list[tuple[str, str]]                # (link text, target id) for every internal link
    removed_lines: Counter = field(default_factory=Counter)  # boilerplate removed, for review


def _tag(el) -> str:
    return el.tag.lower() if isinstance(el.tag, str) else ""   # comments have non-string tags


def _hidden(el) -> bool:
    style = (el.get("style") or "").replace(" ", "").lower()
    return "display:none" in style


def _norm(s: str) -> str:
    return WS_RE.sub(" ", s)


class _Writer:
    def __init__(self, targets: set[str]):
        self.parts: list[str] = []
        self.targets = targets

    def text(self, s: str | None) -> None:
        if s:
            s = _norm(s)
            if s.strip() or (self.parts and not self.parts[-1].endswith(("\n", " "))):
                self.parts.append(s)

    def newline(self) -> None:
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def mark(self, el) -> None:
        for attr in ("id", "name"):
            v = el.get(attr)
            if v and v in self.targets:
                self.parts.append(f"{MARK_OPEN}{v}{MARK_CLOSE}")


def _inline_text(el, w: _Writer) -> str:
    """Text of a table cell, with anchor markers, no line breaks."""
    sub = _Writer(w.targets)

    def rec(e):
        if _tag(e) in SKIP_TAGS or _hidden(e):
            return
        sub.mark(e)
        sub.text(e.text)
        for c in e:
            rec(c)
            sub.text(c.tail)

    rec(el)
    return "".join(sub.parts).replace("\n", " ").strip()


def _table(el, w: _Writer) -> None:
    rows = []
    for tr in el.iter("tr"):
        cells = []
        for cell in tr:
            if _tag(cell) not in ("td", "th") or _hidden(cell):
                continue
            c = _inline_text(cell, w)
            if c in (")", "%") and cells:        # "(321" + ")" -> "(321)"
                cells[-1] += c
            elif c not in DROP_CELLS:
                cells.append(c)
        if cells:
            rows.append(cells)
    if not rows:
        return
    multi = sum(len(r) > 1 for r in rows) >= 2   # layout tables (bullets, headings) are 1 column
    w.newline()
    if multi:
        w.parts.append("[TABLE]\n")
    for r in rows:
        if r[0] in BULLETS and len(r) > 1:       # layout bullet: "•" cell + text cell
            w.parts.append(r[0] + " " + " ".join(r[1:]) + "\n")
        else:
            w.parts.append(" | ".join(r) + "\n")
    if multi:
        w.parts.append("[/TABLE]\n")


def _walk(el, w: _Writer) -> None:
    tag = _tag(el)
    if tag in SKIP_TAGS or _hidden(el):
        return
    if tag == "table":
        w.mark(el)
        _table(el, w)
        return
    block = tag in BLOCK_TAGS
    if block:
        w.newline()
    w.mark(el)
    w.text(el.text)
    for child in el:
        _walk(child, w)
        w.text(child.tail)
    if block:
        w.newline()


# Bare page-header lines: never content on their own (real headings carry a title).
HEADER_RE = re.compile(r"(part\s+[ivx]+|item\s*\d{1,2}[a-c]?\.?|table of contents|\d{1,3})", re.I)


def _remove_boilerplate(lines: list[str], min_repeats: int = 8, max_len: int = 60):
    """Drop running headers/footers and page numbers.

    Removed if, outside tables, a line is
      - a bare header pattern ("PART II", "Item 1A", "Table of Contents", "12") seen 2+ times, or
      - any short line repeated min_repeats+ times (company-name footers etc.).
    The threshold is high on purpose: short labels like "United States" repeat
    5-7 times in energy filings and are real content.
    """
    def key(line):
        return MARK_RE.sub("", line).strip()

    counts, in_table = Counter(), False
    for line in lines:
        k = key(line)
        if k == "[TABLE]":
            in_table = True
        elif k == "[/TABLE]":
            in_table = False
        elif not in_table and k and len(k) <= max_len:
            counts[k] += 1

    kept, removed, in_table = [], Counter(), False
    for line in lines:
        k = key(line)
        if k in ("[TABLE]", "[/TABLE]"):
            in_table = k == "[TABLE]"
            kept.append(line)
            continue
        bare_header = HEADER_RE.fullmatch(k) and (counts[k] >= 2 or k.isdigit())
        boiler = not in_table and k and (bare_header or counts[k] >= min_repeats)
        if boiler:
            removed[k] += 1
            ids = MARK_RE.findall(line)
            if ids:                              # never lose an anchor
                kept.append("".join(f"{MARK_OPEN}{i}{MARK_CLOSE}" for i in ids))
        elif k or MARK_RE.search(line):
            kept.append(line.strip())
    return kept, removed


def extract(path: str | Path) -> Document:
    parser = etree.HTMLParser(huge_tree=True, recover=True)
    root = etree.parse(str(path), parser).getroot()

    links = []
    for a in root.iter("a"):
        href = a.get("href") or ""
        if href.startswith("#") and len(href) > 1:
            links.append((_norm("".join(a.itertext())).strip(), href[1:]))
    w = _Writer({t for _, t in links})

    body = root.find("body")
    _walk(body if body is not None else root, w)

    lines, removed = _remove_boilerplate("".join(w.parts).split("\n"))
    text, anchors = _resolve_markers(lines)
    return Document(text=text, anchors=anchors, links=links, removed_lines=removed)


def _resolve_markers(lines: list[str]) -> tuple[str, dict[str, int]]:
    """Strip anchor markers, recording each one's character offset in the final text.
    A line holding only markers attaches them to the start of the next text line."""
    anchors: dict[str, int] = {}
    out, offset, pending = [], 0, []
    for line in lines:
        pieces = MARK_RE.split(line)                 # [text, id, text, id, ..., text]
        raw = "".join(pieces[0::2])
        clean = raw.strip()
        if not clean:
            pending += pieces[1::2]
            continue
        for a in pending:
            anchors.setdefault(a, offset)
        pending = []
        lead, pos = len(raw) - len(raw.lstrip()), 0
        for i, piece in enumerate(pieces):
            if i % 2 == 0:
                pos += len(piece)
            else:
                anchors.setdefault(piece, offset + min(max(pos - lead, 0), len(clean)))
        out.append(clean)
        offset += len(clean) + 1                     # +1 for the newline
    return "\n".join(out), anchors