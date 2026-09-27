"""Extract local paper/template evidence without changing the inputs."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from lxml import etree as ET
from pypdf import PdfReader

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def docx_content(path):
    result = {"parts": {}, "paragraphs": [], "tables": []}
    parser = ET.XMLParser(resolve_entities=False, no_network=True)
    with ZipFile(path) as z:
        for name in z.namelist():
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            root = ET.fromstring(z.read(name), parser)
            texts = root.xpath("//w:t/text()", namespaces=NS)
            if texts:
                result["parts"][name] = texts
            if name != "word/document.xml":
                continue
            result["paragraphs"] = ["".join(p.xpath(".//w:t/text()", namespaces=NS))
                                    for p in root.xpath("/w:document/w:body/w:p", namespaces=NS)]
            result["tables"] = [
                [["".join(c.xpath(".//w:t/text()", namespaces=NS))
                  for c in row.findall(f"{{{W}}}tc")]
                 for row in table.findall(f"{{{W}}}tr")]
                for table in root.xpath("/w:document/w:body/w:tbl", namespaces=NS)
            ]
            section = root.find(f"{{{W}}}body/{{{W}}}sectPr")
            result["last_section_xml"] = ET.tostring(section, encoding="unicode") if section is not None else None
    return result


def extract(papers, template, out):
    out = Path(out).resolve()
    inputs = [Path(p).resolve() for p in papers] + ([Path(template).resolve()] if template else [])
    for p in inputs:
        if not p.is_file():
            raise FileNotFoundError(p)
    destinations = [out / "sources.json"] + [out / f"paper-{i:03d}.txt" for i in range(1, len(papers) + 1)]
    if template:
        destinations.append(out / "template.json")
    if any(p.exists() for p in destinations) or any(p in inputs for p in destinations):
        raise FileExistsError("Use a fresh output directory; evidence files already exist or overlap input.")
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, path in enumerate(inputs[:len(papers)], 1):
        reader = PdfReader(path)
        pages = [p.extract_text() or "" for p in reader.pages]
        target = out / f"paper-{i:03d}.txt"
        target.write_text("\n\n".join(f"=== PDF PAGE {n} ===\n{text}" for n, text in enumerate(pages, 1)), encoding="utf-8")
        manifest.append({"role": "paper", "path": str(path), "sha256": sha256(path),
                         "pages": len(pages), "text_file": target.name,
                         "empty_text_pages": [n for n, text in enumerate(pages, 1) if not text.strip()]})
    if template:
        path = Path(template).resolve()
        (out / "template.json").write_text(json.dumps(docx_content(path), ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.append({"role": "template", "path": str(path), "sha256": sha256(path)})
    (out / "sources.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--paper", action="append", required=True)
    p.add_argument("--template")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    print(json.dumps(extract(a.paper, a.template, a.out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
