"""
Tests for the section chunker. A word-count tokenizer stands in for bge's
(1 word = 1 token), so the tests run without downloading a model.
"""

from sectra.ingestion.chunker import chunk_section, is_heading

META = dict(accession_no="0000002488-26-000018", ticker="AMD", cik="0000002488",
            fiscal_year=2025, form_type="10-K", item_code="1A", source_url="https://example")


def count(s: str) -> int:
    return len(s.split())


def para(tag: str, i: int, n: int = 40) -> str:
    return f"{tag} paragraph {i}: " + " ".join(f"w{j}." if j % 12 == 11 else f"w{j}" for j in range(n))


def build():
    lines = ["Item 1A. Risk Factors", "Risks Related to Our Supply Chain"]
    lines += [para("Supply", i) for i in range(12)]
    lines += ["Risks Related to Competition"] + [para("Compete", i) for i in range(6)]
    lines += [para("Huge", 0, 900)]                                    # one paragraph > target
    lines += ["Segment results:", "[TABLE]", "Segment | 2025 | 2024"]
    lines += [f"Seg{i} | {i * 10} | {i * 9}" for i in range(150)] + ["[/TABLE]"]
    lines += [para("After", 0), "Trailing Heading At End"]
    return lines, chunk_section("\n".join(lines), META, count, target=350, overlap=50)


def test_ids_are_stable_and_sequential():
    _, chunks = build()
    assert [c["seq"] for c in chunks] == list(range(len(chunks)))
    assert chunks[0]["chunk_id"] == "0000002488-26-000018_1A_000"


def test_size_bounded():
    _, chunks = build()
    assert max(c["n_tokens"] for c in chunks) <= 350 + 50 + 25     # target + overlap + header


def test_no_content_lost():
    lines, chunks = build()
    text = "\n".join(c["text"] for c in chunks)
    for line in lines:
        if line not in ("[TABLE]", "[/TABLE]", "Trailing Heading At End") and not line.startswith("Huge"):
            assert line in text, line
    assert all(f"w{j}" in text for j in range(0, 900, 37))           # long paragraph split by sentence


def test_big_table_split_with_header_repeated():
    _, chunks = build()
    pieces = [part for c in chunks for part in c["text"].split("[TABLE]\n")[1:]]
    assert len(pieces) >= 2
    assert all(p.startswith("Segment | 2025 | 2024") for p in pieces)


def test_heading_never_ends_a_chunk():
    _, chunks = build()
    for c in chunks:
        last = c["text"].split("\n")[-1]
        assert last == "[/TABLE]" or not is_heading(last), last


def test_subheading_goes_into_header():
    _, chunks = build()
    assert "Item 1A. Risk Factors" not in chunks[0]["header"]
    assert "Supply Chain" in chunks[0]["header"]
    starts_compete = [c for c in chunks if c["text"].startswith("Compete paragraph")]
    assert starts_compete and all("Competition" in c["header"] for c in starts_compete)


def test_consecutive_chunks_overlap():
    _, chunks = build()
    a, b = [c for c in chunks if "Supply paragraph" in c["text"]][:2]
    assert set(a["text"].split("\n")) & set(b["text"].split("\n"))


def test_no_overlap_only_or_duplicate_chunks():
    lines = []
    for i in range(6):                       # small line then a block that fills a chunk on its own
        lines += [f"Small {i}. " + " ".join(["x"] * 28), f"Big {i}. " + " ".join(["y"] * 328)]
    chunks = chunk_section("\n".join(lines), META, count, target=350, overlap=50)
    bodies = [c["text"] for c in chunks]
    assert len(set(bodies)) == len(bodies)
    text = "\n".join(bodies)
    assert all(line in text for line in lines)


def test_short_line_lists_do_not_pile_up():
    # e.g. a list of executive officers or products: short lines, no punctuation
    lines = ["Executive Officers"] + [f"Person Number {i} Senior Vice President" for i in range(120)]
    chunks = chunk_section("\n".join(lines), META, count, target=350, overlap=50)
    assert len(chunks) >= 2
    assert max(c["n_tokens"] for c in chunks) <= 350 + 50 + 25
    text = "\n".join(c["text"] for c in chunks)
    assert all(line in text for line in lines[1:])


def test_giant_table_row_is_split():
    bio = " ".join(f"word{j}" for j in range(700))             # e.g. an executive bio in one cell
    lines = ["[TABLE]", "Name | Age | Business experience", f"Jane Doe | 54 | {bio}",
             "John Roe | 60 | Short bio.", "[/TABLE]", "After the table."]
    chunks = chunk_section("\n".join(lines), META, count, target=350, overlap=50)
    assert max(c["n_tokens"] for c in chunks) <= 350 + 50 + 25
    text = "\n".join(c["text"] for c in chunks)
    assert all(f"word{j}" in text for j in range(700)) and "John Roe" in text
    pieces = [p for c in chunks for p in c["text"].split("[TABLE]\n")[1:]]
    assert all(p.startswith("Name | Age | Business experience") for p in pieces)