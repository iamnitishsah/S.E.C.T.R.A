"""Split a cleaned 10-K (from html_text.extract) into its Items.

Start of an Item:
  1. Table-of-contents links are the primary signal, but a link's target is only
     accepted if the text it lands on looks like that Item's heading (its number,
     "Item 1A", or its title, "Risk Factors"). Rejects links to subsections.
  2. Fallback: heading lines found in the text ("Item 1A. Risk Factors" at the start
     of a line; cross-references like "Item 1A of this Form 10-K" are rejected).
  3. Of all valid candidates, the first with a real body (>= MIN_BODY chars) wins.
     That skips TOC entries and pointer stubs ("see the Financial Section").
     Items that are legitimately short ("Item 1B. None.") take the link-verified
     candidate, or else the last one (the TOC always comes before the body).
End of an Item: the next Item-level heading (any other Item), or an end marker
such as the auditor's report, so MD&A never runs into the financial statements.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sectra.parsing.html_text import Document

# (code, title regex matched at the start of a line/label, exact=True: title must be the whole label)
ITEMS: list[tuple[str, str, bool]] = [
    ("1", r"business", True),
    ("1A", r"risk\s+factors", False),
    ("1B", r"unresolved\s+staff\s+comments", False),
    ("1C", r"cybersecurity", True),
    ("2", r"properties", True),
    ("3", r"legal\s+proceedings", False),
    ("4", r"mine\s+safety\s+disclosures?", False),
    ("5", r"market\s+for\s+(the\s+)?registrant", False),
    ("6", r"(\[\s*reserved\s*\]|reserved|selected\s+financial\s+data)", False),
    ("7", r"management.s\s+discussion\s+and\s+analysis", False),
    ("7A", r"quantitative\s+and\s+qualitative\s+disclosures?\s+about\s+market\s+risk", False),
    ("8", r"financial\s+statements\s+and\s+supplementary\s+data", False),
    ("9", r"changes\s+in\s+and\s+disagreements\s+with\s+accountants", False),
    ("9A", r"controls\s+and\s+procedures", False),
    ("9B", r"other\s+information", True),
    ("9C", r"disclosure\s+regarding\s+foreign\s+jurisdictions", False),
    ("10", r"directors,?\s+executive\s+officers", False),
    ("11", r"executive\s+compensation", True),
    ("12", r"security\s+ownership\s+of\s+certain", False),
    ("13", r"certain\s+relationships\s+and\s+related", False),
    ("14", r"principal\s+account\w*\s+fees", False),
    ("15", r"exhibits?,?\s+(and\s+)?financial\s+statement\s+schedules", False),
    ("16", r"form\s+10-k\s+summary", False),
]
TITLES = {code: re.compile(pat, re.I) for code, pat, _ in ITEMS}
FULL_TITLE_SUFFIX = {
    "7": r".*",
    "7A": r"s?",
    "5": r".*", "9": r".*", "9C": r".*", "10": r".*", "12": r".*", "13": r".*", "14": r".*", "15": r".*",
}
FULL_TITLES = {code: re.compile(pat + FULL_TITLE_SUFFIX.get(code, ""), re.I) for code, pat, _ in ITEMS}
EXACT = {code for code, _, exact in ITEMS if exact}
ORDER = [code for code, _, _ in ITEMS]

ITEM_NUM_RE = re.compile(r"item\s*(\d{1,2}[a-c]?)\b[\s.:\-\u2013\u2014]*", re.I)
END_MARKERS = re.compile(
    r"(reports?\s+of\s+independent\s+registered\s+public\s+accounting\s+firm"
    r"|reports?\s+of\s+management\b"
    r"|management.s\s+report\s+on\s+internal\s+control"
    r"|signatures?$)",
    re.I,
)
MIN_BODY = 1_000          # shorter "sections" are TOC rows or pointer stubs
MAX_HEADING_LEN = 200     # headings are short; longer lines are sentences
PUNCT_END = ".:;,"


@dataclass
class Section:
    item: str
    start: int            # char offset in Document.text
    end: int
    method: str           # "toc_link" (link-verified) or "heading" (text fallback)
    heading: str          # the heading line, for review

    @property
    def length(self) -> int:
        return self.end - self.start


def _clean(line: str) -> str:
    return line.replace(" | ", " ").strip()   # headings can sit in table cells


def _title_code(text: str) -> str | None:
    t = text.strip().rstrip(PUNCT_END).strip()
    for code in ORDER:
        m = TITLES[code].match(t)
        if not m:
            continue
        if code in EXACT:
            if m.end() == len(t):
                return code
        else:
            return code
    return None


def numbered_heading_code(line: str) -> str | None:
    """'Item 1A. Risk Factors' / 'ITEM 7.' -> code. 'Item 1A of this Form 10-K...' -> None."""
    line = _clean(line)
    if len(line) > MAX_HEADING_LEN:
        return None
    m = ITEM_NUM_RE.match(line)
    if not m:
        return None
    code = m.group(1).upper()
    if code not in TITLES:
        return None
    rest = line[m.end():].strip()
    rest = re.sub(r"\s+\d{1,3}$", "", rest)          # TOC rows end in a page number
    if not rest or TITLES[code].match(rest.rstrip(PUNCT_END)):
        return code
    return None


def title_heading_code(line: str) -> str | None:
    """A heading made of the whole title alone: 'Management's Discussion and Analysis of
    Financial Condition and Results of Operations'. 'Risk Factors Summary:' -> None."""
    t = _clean(line).rstrip(PUNCT_END).strip()
    if len(t) > MAX_HEADING_LEN:
        return None
    for code in ORDER:
        if FULL_TITLES[code].fullmatch(t):
            return code
    return None


def link_code(label: str) -> str | None:
    label = _clean(label)
    m = ITEM_NUM_RE.match(label)
    if m and m.group(1).upper() in TITLES:
        return m.group(1).upper()
    return _title_code(label)


def split(doc: Document) -> dict[str, Section]:
    lines = doc.text.split("\n")
    starts, pos = [], 0
    for line in lines:
        starts.append(pos)
        pos += len(line) + 1

    def line_at(offset: int) -> int:                  # binary search: line containing offset
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo

    numbered = {i: c for i, l in enumerate(lines) if (c := numbered_heading_code(l))}
    ends = {i for i, l in enumerate(lines) if END_MARKERS.match(_clean(l))}

    # Link targets, verified: the anchor must land on (or just before) that Item's heading.
    linked: dict[str, set[int]] = {}
    for label, target in doc.links:
        code = link_code(label)
        if not code or target not in doc.anchors:
            continue
        i = line_at(doc.anchors[target])
        for j in range(i, min(i + 3, len(lines))):    # allow e.g. "PART II" just above
            if numbered.get(j) == code or title_heading_code(lines[j]) == code:
                linked.setdefault(code, set()).add(j)
                break
            if len(lines[j]) > 40:                    # real text reached: not a heading
                break

    # Boundaries: every numbered heading, every verified linked heading, end markers.
    boundary: dict[int, str | None] = dict(numbered)
    for code, idxs in linked.items():
        for i in idxs:
            boundary.setdefault(i, code)
    for i in ends:
        boundary.setdefault(i, None)
    bpos = sorted(boundary)

    def end_of(i: int, code: str) -> int:
        for b in bpos:
            if b > i and boundary[b] != code:
                return starts[b]
        return len(doc.text)

    sections: dict[str, Section] = {}
    for code in ORDER:
        cands = sorted(set(linked.get(code, set())) | {i for i, c in numbered.items() if c == code})
        if not cands:
            continue
        options = [
            Section(code, starts[i], end_of(i, code),
                    "toc_link" if i in linked.get(code, set()) else "heading", lines[i][:120])
            for i in cands
        ]
        chosen = (
                next((s for s in options if s.length >= MIN_BODY), None)      # first with a real body
                or next((s for s in options if s.method == "toc_link"), None)  # short Item ("None."): trust the link
                or options[-1]                                                  # no link: TOC comes first, body last
        )
        sections[code] = chosen
    return sections