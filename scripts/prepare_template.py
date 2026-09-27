"""Copy a DOCX and remove only explicitly matched VML watermark shapes."""
import argparse
from copy import copy
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree as ET

DEFAULT_PHRASES = ["James科研小班课", "James的科研小班课"]
NS = {"v": "urn:schemas-microsoft-com:vml"}


def normalize(value):
    return re.sub(r"\s+", "", value)


def prepare(source, destination, phrases=None):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError("Input must remain unchanged; choose a different output.")
    if destination.exists():
        raise FileExistsError(destination)
    phrases = DEFAULT_PHRASES if phrases is None else phrases
    if not phrases or any(not normalize(p) for p in phrases):
        raise ValueError("Watermark phrases must be nonempty.")
    raw = source.read_bytes()
    before = hashlib.sha256(raw).hexdigest()
    changes = []
    parser = ET.XMLParser(resolve_entities=False, no_network=True)
    with ZipFile(source) as z:
        entries = [(copy(info), z.read(info.filename)) for info in z.infolist()]
    edited = []
    for info, data in entries:
        removed = 0
        if re.fullmatch(r"word/(header|footer)\d+\.xml", info.filename):
            root = ET.fromstring(data, parser)
            for shape in list(root.xpath(".//v:shape", namespaces=NS)):
                text = "".join(shape.xpath(".//v:textpath/@string", namespaces=NS))
                if any(normalize(p) in normalize(text) for p in phrases):
                    shape.getparent().remove(shape)
                    removed += 1
            if removed:
                data = ET.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
                changes.append({"part": info.filename, "removed_shapes": removed})
        edited.append((info, data))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream, ZipFile(stream, "w", ZIP_DEFLATED) as z:
        for info, data in edited:
            z.writestr(info, data)
    if hashlib.sha256(source.read_bytes()).hexdigest() != before:
        raise RuntimeError("Source changed during operation.")
    return {"source_sha256": before, "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "changed_parts": changes, "removed_shapes": sum(c["removed_shapes"] for c in changes),
            "requires_visual_review": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--phrase", action="append")
    a = p.parse_args()
    print(json.dumps(prepare(a.input, a.output, a.phrase), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
