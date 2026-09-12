#!/usr/bin/env python3
"""
Turn a pandoc-produced .docx into review format, in place.

pandoc has no way to emit either of the two things a journal means by "review
format" in Word, because both are document properties rather than content:

  - **line numbers** live in the section properties as <w:lnNumType>
  - **line spacing** lives in the style defaults as <w:spacing w:line=...>

Both are edited directly in the OOXML here. The element order inside <w:sectPr>
is fixed by the schema -- lnNumType must follow pgMar and precede cols -- and
Word silently refuses to open a file that gets it wrong, so the insertion is
anchored rather than appended.
"""
import re
import shutil
import zipfile
from pathlib import Path

LINE_NUMBERS = '<w:lnNumType w:countBy="1" w:restart="continuous" w:distance="360"/>'
# 360 twentieths of a point = 1.5 line spacing at Word's 240 baseline
SPACING = '<w:spacing w:after="0" w:line="360" w:lineRule="auto"/>'


# CT_SectPr children must appear in this order. Word rejects a file that gets
# it wrong, so the section is rebuilt in order rather than patched -- inserting
# straight after <w:sectPr> breaks any document carrying a footnotePr, which
# pandoc's output does.
_SECTPR_ORDER = ["footnotePr", "endnotePr", "type", "pgSz", "pgMar", "paperSrc",
                 "pgBorders", "lnNumType", "pgNumType", "cols", "formProt",
                 "vAlign", "noEndnote", "titlePg", "textDirection", "bidi",
                 "rtlGutter", "docGrid", "printerSettings"]

# US Letter with 1 inch margins, in twentieths of a point. The tex2docx
# reference document defines no page geometry at all, so without this the page
# size falls back to the reader's Word locale -- Letter in the US, A4 in
# Europe -- and a submission should not depend on that.
PAGE_SIZE = '<w:pgSz w:w="12240" w:h="15840"/>'
PAGE_MARGINS = ('<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" '
                'w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>')


def _rebuild_sectpr(document_xml: str) -> tuple[str, bool]:
    m = re.search(r"(<w:sectPr[^>]*>)(.*?)(</w:sectPr>)", document_xml, re.S)
    if not m:
        return document_xml, False
    open_tag, body, close_tag = m.groups()

    existing = {}
    for tag in _SECTPR_ORDER:
        for pat in (rf"<w:{tag}\b[^>]*/>", rf"<w:{tag}\b[^>]*>.*?</w:{tag}>"):
            hit = re.search(pat, body, re.S)
            if hit:
                existing[tag] = hit.group(0)
                break

    existing.setdefault("pgSz", PAGE_SIZE)
    existing.setdefault("pgMar", PAGE_MARGINS)
    existing["lnNumType"] = LINE_NUMBERS

    new_body = "".join(existing[t] for t in _SECTPR_ORDER if t in existing)
    rebuilt = open_tag + new_body + close_tag
    return document_xml[:m.start()] + rebuilt + document_xml[m.end():], True


def _add_line_numbers(document_xml: str) -> tuple[str, bool]:
    return _rebuild_sectpr(document_xml)


def _set_spacing(styles_xml: str) -> tuple[str, bool]:
    m = re.search(r"<w:docDefaults>.*?</w:docDefaults>", styles_xml, re.S)
    if not m:
        return styles_xml, False
    block = m.group(0)
    if 'w:line="360"' in block:
        return styles_xml, False
    if "<w:pPrDefault>" in block:
        new = re.sub(r"(<w:pPrDefault>\s*<w:pPr>)", r"\1" + SPACING, block, count=1)
        if new == block:  # <w:pPrDefault/> self-closing, or no inner pPr
            new = block.replace("<w:pPrDefault/>",
                                f"<w:pPrDefault><w:pPr>{SPACING}</w:pPr></w:pPrDefault>")
    else:
        new = block.replace("<w:docDefaults>",
                            f"<w:docDefaults><w:pPrDefault><w:pPr>{SPACING}</w:pPr></w:pPrDefault>")
    return styles_xml.replace(block, new, 1), new != block


def apply(path: Path) -> dict:
    """Rewrite path in place. Returns what changed."""
    path = Path(path)
    tmp = path.with_suffix(".docx.tmp")
    result = {"line_numbers": False, "spacing": False}
    with zipfile.ZipFile(path) as zin, \
         zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                text, changed = _add_line_numbers(data.decode("utf8"))
                result["line_numbers"] = changed
                data = text.encode("utf8")
            elif item.filename == "word/styles.xml":
                text, changed = _set_spacing(data.decode("utf8"))
                result["spacing"] = changed
                data = text.encode("utf8")
            zout.writestr(item, data)
    shutil.move(tmp, path)
    return result


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        r = apply(Path(arg))
        print(f"  {Path(arg).name}: line_numbers={r['line_numbers']} spacing={r['spacing']}")
