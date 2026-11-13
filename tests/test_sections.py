"""Tests for 10-K text extraction and Item splitting.

Each mock filing reproduces a layout found in the real data:
  AAPL - TOC links labelled "Item 1A.", cross-references in the text
  MSFT - links labelled by title, headings split across <span>s, running page headers
  CVX  - Item 7 is a one-line pointer; real MD&A sits in a later Financial Section;
         links to subsections; cross-references that look exactly like headings
  QCOM - a linked "Risk Factors Summary" before the real Item 1A
  EOG  - no table-of-contents links at all (text fallback)
Run: pytest tests/test_sections.py -v
"""

from pathlib import Path

import pytest

from sectra.parsing.html_text import extract
from sectra.parsing.section_splitter import numbered_heading_code, split, title_heading_code


def body(word: str, n: int = 40) -> str:
    return "".join(f"<p>{word} sentence number {i} describing the business in detail.</p>" for i in range(n))


@pytest.fixture
def make_doc(tmp_path: Path):
    def _make(html: str, name: str = "filing", encoding: str = "utf-8"):
        path = tmp_path / f"{name}.htm"
        page = f'<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><body>{html}</body></html>'
        path.write_bytes(page.encode(encoding))
        return extract(path)
    return _make


def section_text(doc, sections, code: str) -> str:
    s = sections[code]
    return doc.text[s.start:s.end]


# ---------------------------------------------------------------- html_text

def test_hidden_xbrl_header_is_dropped(make_doc):
    doc = make_doc('<div style="display:none"><ix:header>HIDDEN CONTEXT</ix:header></div><p>Visible.</p>')
    assert "HIDDEN" not in doc.text and "Visible." in doc.text


def test_spans_do_not_split_words(make_doc):
    doc = make_doc("<div><span>ITEM 1A. RIS</span><span>K FACTORS</span></div>")
    assert "ITEM 1A. RISK FACTORS" in doc.text


def test_whitespace_and_nbsp_normalised(make_doc):
    doc = make_doc("<p>Our business&#160;faces   many risks.</p>")
    assert "Our business faces many risks." in doc.text


def test_running_headers_and_page_numbers_removed(make_doc):
    pages = "".join(f"<div>PART I</div><div>Item 1A</div><div>{n}</div><p>Risk text {n}.</p>" for n in range(12, 15))
    doc = make_doc(pages)
    lines = doc.text.split("\n")
    assert "Item 1A" not in lines and "PART I" not in lines and "13" not in lines
    assert "Risk text 13." in lines
    assert doc.removed_lines["Item 1A"] == 3


def test_repeated_content_labels_are_kept(make_doc):
    # Energy filings repeat region names 5-7 times; they are content, not footers.
    doc = make_doc("".join(f"<div>Africa</div><p>Production rose {i}%.</p>" for i in range(6)))
    assert doc.text.count("Africa") == 6


def test_single_bare_heading_is_kept(make_doc):
    doc = make_doc("<div>ITEM 2.</div><div>PROPERTIES</div><p>We own offices.</p>")
    assert "ITEM 2." in doc.text


def test_financial_table_rows(make_doc):
    doc = make_doc("""<table>
        <tr><td>Millions</td><td>2025</td><td>2024</td></tr>
        <tr><td>Net sales</td><td>$</td><td>416,161</td><td>$</td><td>391,035</td></tr>
        <tr><td>Other income</td><td>(321</td><td>)</td><td>269</td></tr></table>""")
    assert "[TABLE]" in doc.text and "[/TABLE]" in doc.text
    assert "Net sales | 416,161 | 391,035" in doc.text
    assert "Other income | (321) | 269" in doc.text


def test_layout_bullet_table_becomes_plain_line(make_doc):
    doc = make_doc("<table><tr><td>&#8226;</td><td>A bullet point.</td></tr></table>")
    assert "• A bullet point." in doc.text and "[TABLE]" not in doc.text


def test_anchor_offsets_point_at_headings(make_doc):
    doc = make_doc('<p><a href="#h">Risk Factors</a></p><div>Item 1A</div><div>Item 1A</div>'
                   '<div id="h">ITEM 1A. RISK FACTORS</div><p>Text.</p>')
    assert doc.text[doc.anchors["h"]:].startswith("ITEM 1A. RISK FACTORS")


def test_windows_1252_file_decodes(make_doc):
    doc = make_doc("<div>Item 7. Management\u2019s Discussion and Analysis</div>", encoding="cp1252")
    assert "Management\u2019s Discussion" in doc.text


# ------------------------------------------------------- heading detection

@pytest.mark.parametrize("line, code", [
    ("Item 1A. Risk Factors", "1A"),
    ("ITEM 7.", "7"),
    ("Item 7. Management\u2019s Discussion and Analysis of Financial Condition", "7"),
    ("Item 1A. | Risk Factors | 5", "1A"),                       # TOC row in a table
    ("Item 10. Directors, Executive Officers and Corporate Governance", "10"),
    ("Item 1A of this Form 10-K under the heading Risk Factors.", None),   # cross-reference
    ("Item 7 of the Company\u2019s Annual Report on Form 10-K", None),
])
def test_numbered_heading_code(line, code):
    assert numbered_heading_code(line) == code


@pytest.mark.parametrize("line, code", [
    ("RISK FACTORS", "1A"),
    ("Risk Factors Summary:", None),                              # QCOM
    ("Management\u2019s Discussion and Analysis of Financial Condition and Results of Operations", "7"),
    ("Business", "1"),
    ("Business Environment and Outlook", None),
    ("Environmental Matters", None),
])
def test_title_heading_code(line, code):
    assert title_heading_code(line) == code


# ----------------------------------------------------------------- split()

def test_aapl_layout(make_doc):
    doc = make_doc(f"""
    <table><tr><td><a href="#a1a">Item 1A.</a></td><td><a href="#a1a">Risk Factors</a></td><td>5</td></tr>
    <tr><td><a href="#a1b">Item 1B.</a></td><td>Unresolved Staff Comments</td><td>20</td></tr>
    <tr><td><a href="#a7">Item 7.</a></td><td>MD&amp;A</td><td>30</td></tr></table>
    <p>Forward-looking statements are discussed in Part I,</p>
    <p>Item 1A of this Form 10-K under the heading Risk Factors.</p>
    <div>Item 1. Business</div>{body('Business')}
    <div id="a1a">Item 1A. Risk Factors</div>{body('Risk')}
    <div id="a1b">Item 1B. Unresolved Staff Comments</div><p>None.</p>
    <div id="a7">Item 7. Management\u2019s Discussion and Analysis of Financial Condition and Results of Operations</div>{body('MDA')}
    <div>Item 7A. Quantitative and Qualitative Disclosures About Market Risk</div>{body('Market')}
    """)
    secs = split(doc)
    risk = section_text(doc, secs, "1A")
    assert secs["1A"].method == "toc_link"
    assert "Risk sentence number 39" in risk and "Unresolved" not in risk
    assert section_text(doc, secs, "1B").strip().endswith("None.")      # short Item kept
    mda = section_text(doc, secs, "7")
    assert "MDA sentence number 39" in mda and "Market sentence" not in mda


def test_msft_layout(make_doc):
    pages = "".join(f"<div>PART I</div><div>Item 1A</div><div>{n}</div>{body('Risk', 10)}" for n in range(3))
    doc = make_doc(f"""
    <table><tr><td><a href="#item_1a">Risk Factors</a></td><td>14</td></tr>
    <tr><td><a href="#item_7">Management\u2019s Discussion and Analysis of Financial Condition and Results of Operations</a></td><td>40</td></tr></table>
    <div id="item_1a"><span>ITEM 1A. RIS</span><span>K FACTORS</span></div>{pages}
    <div>ITEM 1B. UNRESOLVED STAFF COMMENTS</div><p>None.</p>
    <div id="item_7">ITEM 7. MANAGEMENT\u2019S DISCUSSION AND ANALYSIS</div>{body('MDA')}
    <div>ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK</div>{body('Market')}
    """)
    secs = split(doc)
    risk = section_text(doc, secs, "1A")
    assert secs["1A"].heading.startswith("ITEM 1A. RISK FACTORS")
    assert risk.count("Risk sentence") == 30 and "\nItem 1A\n" not in risk
    assert "QUANTITATIVE" not in section_text(doc, secs, "7")


def test_cvx_layout_skips_pointer_and_subsections(make_doc):
    doc = make_doc(f"""
    <table><tr><td><a href="#c1a">Risk Factors</a></td><td>20</td></tr>
    <tr><td><a href="#c7">Management\u2019s Discussion and Analysis of Financial Condition and Results of Operations</a></td><td>30</td></tr></table>
    <div>Item 1. Business</div>{body('Business')}
    <p>See <a href="#c1a">Item 1A. Risk Factors</a> for greenhouse gas risks.</p>
    <div id="c1a">Item 1A. Risk Factors</div>{body('Risk', 25)}
    <div id="cgen">GENERAL RISK FACTORS</div>{body('General', 10)}
    <p>As discussed in <a href="#cgen">Item 1A. Risk Factors</a> on pages 21 through 24.</p>
    <div>Item 1B. Unresolved Staff Comments</div><p>None.</p>
    <div id="c7">Item 7. Management\u2019s Discussion and Analysis of Financial Condition and Results of Operations</div>
    <p>The index to MD&amp;A is presented in the Financial Table of Contents.</p>
    <div>Item 7A. Quantitative and Qualitative Disclosures About Market Risk</div><p>Contained in MD&amp;A.</p>
    <div>Item 8. Financial Statements and Supplementary Data</div><p>See the Financial Table of Contents.</p>
    <table><tr><td><a href="#cmda">Management\u2019s Discussion and Analysis of</a></td><td>35</td></tr>
    <tr><td><a href="#cenv">Management\u2019s Discussion and Analysis of</a></td><td>50</td></tr></table>
    <div id="cmda">Management\u2019s Discussion and Analysis of Financial Condition and Results of Operations \u2014 Overview</div>{body('RealMDA')}
    <div id="cenv">Environmental Matters</div>{body('Environment', 10)}
    <div>Reports of Management</div>{body('Audit')}
    """)
    secs = split(doc)
    risk = section_text(doc, secs, "1A")
    assert "GENERAL RISK FACTORS" in risk                 # subsection stays inside 1A
    mda = section_text(doc, secs, "7")
    assert secs["7"].heading.startswith("Management")     # pointer stub skipped
    assert "RealMDA sentence number 39" in mda and "Environment sentence" in mda
    assert "Audit" not in mda                             # stops at Reports of Management


def test_qcom_summary_does_not_win(make_doc):
    doc = make_doc(f"""
    <table><tr><td><a href="#sum">Risk Factors Summary</a></td><td>3</td></tr>
    <tr><td><a href="#q1a">Risk Factors</a></td><td>20</td></tr></table>
    <div id="sum">Risk Factors Summary:</div>{body('Summary', 30)}
    <div>Item 1. Business</div>{body('Business')}
    <div id="q1a">Item 1A. Risk Factors</div>{body('Risk', 60)}
    <div>Item 1B. Unresolved Staff Comments</div><p>None.</p>
    """)
    secs = split(doc)
    assert secs["1A"].heading.startswith("Item 1A")
    assert "Summary sentence" not in section_text(doc, secs, "1A")


def test_no_links_text_fallback(make_doc):
    doc = make_doc(f"""
    <div>Item 1A. Risk Factors 5</div><div>Item 7. Management's Discussion and Analysis 30</div>
    <div>Item 1A. Risk Factors</div>{body('Risk')}
    <div>Item 2. Properties</div>{body('Props', 3)}
    <div>Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations</div>{body('MDA')}
    <div>Item 8. Financial Statements and Supplementary Data</div>{body('Stmt')}
    """)
    secs = split(doc)
    assert secs["1A"].method == "heading"
    assert "Risk sentence number 39" in section_text(doc, secs, "1A")    # TOC line skipped
    mda = section_text(doc, secs, "7")
    assert "MDA sentence number 39" in mda and "Stmt" not in mda