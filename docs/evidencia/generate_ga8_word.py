from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
FINAL_DIR = ROOT / "GA8-220501096-AA1-EV02_FINAL"

SOURCES = [
    ROOT / "GA8-220501096-AA1-EV02_modulos_integrados.md",
    ROOT / "GA8-220501096-AA1-EV02_manual_tecnico.md",
    ROOT / "GA8-220501096-AA1-EV02_urls_y_entregables.md",
]


def run(text: str, bold: bool = False) -> str:
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def paragraph(
    text: str = "",
    style: str | None = None,
    align: str | None = None,
    bold: bool = False,
    shading: str | None = None,
) -> str:
    props: list[str] = []
    if style:
        props.append(f'<w:pStyle w:val="{style}"/>')
    if align:
        props.append(f'<w:jc w:val="{align}"/>')
    if shading:
        props.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shading}"/>')
    ppr = f"<w:pPr>{''.join(props)}</w:pPr>" if props else ""
    text = strip_inline_md(text)
    lines = text.split("\n")
    runs: list[str] = []
    for i, line in enumerate(lines):
        runs.append(run(line, bold=bold))
        if i < len(lines) - 1:
            runs.append("<w:r><w:br/></w:r>")
    if not runs:
        runs.append(run("", bold=bold))
    return f"<w:p>{ppr}{''.join(runs)}</w:p>"


def cell(text: str, width: int, bold_text: bool = False, shading: str | None = None) -> str:
    parts = [f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>']
    if shading:
        parts.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shading}"/>')
    parts.append("</w:tcPr>")
    parts.append(paragraph(text, style="TableText", bold=bold_text))
    parts.append("</w:tc>")
    return "".join(parts)


def table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    col_count = max(len(row) for row in rows)
    widths = [9000 // col_count] * col_count
    trs: list[str] = []
    for i, row in enumerate(rows):
        normalized = row + [""] * (col_count - len(row))
        cells = "".join(
            cell(value, widths[idx], bold_text=i == 0, shading="D9EAF7" if i == 0 else None)
            for idx, value in enumerate(normalized)
        )
        trs.append(f"<w:tr>{cells}</w:tr>")
    return (
        "<w:tbl>"
        "<w:tblPr>"
        '<w:tblStyle w:val="TableGrid"/>'
        '<w:tblW w:w="0" w:type="auto"/>'
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="8" w:space="0" w:color="B7C9E2"/>'
        '<w:left w:val="single" w:sz="8" w:space="0" w:color="B7C9E2"/>'
        '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="B7C9E2"/>'
        '<w:right w:val="single" w:sz="8" w:space="0" w:color="B7C9E2"/>'
        '<w:insideH w:val="single" w:sz="6" w:space="0" w:color="D9E2F3"/>'
        '<w:insideV w:val="single" w:sz="6" w:space="0" w:color="D9E2F3"/>'
        "</w:tblBorders>"
        "</w:tblPr>"
        + "".join(trs)
        + "</w:tbl>"
    )


def strip_inline_md(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    return text


def parse_table(lines: list[str], start: int) -> tuple[str, int]:
    rows: list[list[str]] = []
    index = start
    while index < len(lines):
        line = lines[index].rstrip()
        if not line.strip().startswith("|"):
            break
        parts = [strip_inline_md(part.strip()) for part in line.strip().strip("|").split("|")]
        if all(set(part) <= {"-"} for part in parts):
            index += 1
            continue
        rows.append(parts)
        index += 1
    return table(rows), index


def build_document_from_markdown(source: Path) -> str:
    lines = source.read_text(encoding="utf-8").splitlines()
    parts: list[str] = []
    i = 0
    in_code = False
    code_buffer: list[str] = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                code_buffer = []
            else:
                parts.append(paragraph("\n".join(code_buffer), style="CodeBlock", shading="F4F8FC"))
                in_code = False
                code_buffer = []
            i += 1
            continue

        if in_code:
            code_buffer.append(line)
            i += 1
            continue

        if not stripped:
            parts.append(paragraph(""))
            i += 1
            continue

        if stripped.startswith("|"):
            tbl, next_i = parse_table(lines, i)
            parts.append(tbl)
            i = next_i
            continue

        if stripped.startswith("# "):
            parts.append(paragraph(strip_inline_md(stripped[2:].strip()), style="Title", align="center"))
            i += 1
            continue
        if stripped.startswith("## "):
            parts.append(paragraph(strip_inline_md(stripped[3:].strip()), style="Heading1"))
            i += 1
            continue
        if stripped.startswith("### "):
            parts.append(paragraph(strip_inline_md(stripped[4:].strip()), style="Heading2"))
            i += 1
            continue

        if stripped.startswith("- "):
            parts.append(paragraph("• " + strip_inline_md(stripped[2:]), style="BodyText"))
            i += 1
            continue

        if re.match(r"^\d+\.\s+", stripped):
            parts.append(paragraph(strip_inline_md(stripped), style="BodyText"))
            i += 1
            continue

        parts.append(paragraph(stripped, style="BodyText"))
        i += 1

    body = "".join(parts)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        'xmlns:o="urn:schemas-microsoft-com:office:office" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:w10="urn:schemas-microsoft-com:office:word" '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
        'xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" '
        'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" '
        'xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" '
        'xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" '
        'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
        'mc:Ignorable="w14 w15 wp14">'
        f"<w:body>{body}"
        "<w:sectPr>"
        '<w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1200" w:right="1100" w:bottom="1200" w:left="1100" w:header="708" w:footer="708" w:gutter="0"/>'
        "</w:sectPr>"
        "</w:body></w:document>"
    )


def build_styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
    <w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:rPr><w:b/><w:color w:val="1F4E79"/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="Heading1"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:rPr><w:b/><w:color w:val="1F1F1F"/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="Heading2"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:rPr><w:b/><w:color w:val="2F5597"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="BodyText">
    <w:name w:val="BodyText"/><w:basedOn w:val="Normal"/><w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="TableText">
    <w:name w:val="TableText"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="CodeBlock">
    <w:name w:val="CodeBlock"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>
  </w:style>
</w:styles>
"""


def build_content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""


def build_root_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def build_document_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""


def build_core_xml(title: str) -> str:
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{escape(title)}</dc:title>
  <dc:subject>Evidencia GA8</dc:subject>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>
"""


def build_app_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Microsoft Office Word</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <Company>OpenAI</Company>
  <LinksUpToDate>false</LinksUpToDate>
  <SharedDoc>false</SharedDoc>
  <HyperlinksChanged>false</HyperlinksChanged>
  <AppVersion>16.0000</AppVersion>
</Properties>
"""


def build_docx(source: Path, output: Path) -> None:
    title = source.stem.replace("_", " ")
    document_xml = build_document_from_markdown(source)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", build_content_types_xml())
        docx.writestr("_rels/.rels", build_root_rels_xml())
        docx.writestr("docProps/core.xml", build_core_xml(title))
        docx.writestr("docProps/app.xml", build_app_xml())
        docx.writestr("word/document.xml", document_xml)
        docx.writestr("word/styles.xml", build_styles_xml())
        docx.writestr("word/_rels/document.xml.rels", build_document_rels_xml())


def main() -> None:
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    for source in SOURCES:
        output = FINAL_DIR / f"{source.stem}.docx"
        build_docx(source, output)
        print(f"Documento generado: {output}")


if __name__ == "__main__":
    main()
