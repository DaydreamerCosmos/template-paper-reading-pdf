"""Check a final PDF; visual evidence is separate and bound to its exact hash."""
import argparse
import hashlib
import json
from pathlib import Path
import unicodedata

from pypdf import PdfReader

DEFAULT_FORBIDDEN = ["James科研小班课", "James的科研小班课"]


def normalize(text):
    # Ignore line wrapping and compatibility glyph variants; retain punctuation.
    return "".join(unicodedata.normalize("NFKC", text).split())


def check(pdf, requirements, base, visual=None):
    pdf, base = Path(pdf).resolve(), Path(base).resolve()
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    reader = PdfReader(pdf)
    pages = [page.extract_text() or "" for page in reader.pages]
    full = normalize("\n".join(pages))
    urls = set()
    for page in reader.pages:
        for entry in page.get("/Annots", []):
            annotation = entry.get_object()
            action = annotation.get("/A")
            if action:
                uri = action.get_object().get("/URI")
                if uri:
                    urls.add(str(uri))
    required = requirements.get("required_text", [])
    config_errors = []
    for key in ["required_text", "expected_urls", "forbidden_text"]:
        value = requirements.get(key, [] if key != "forbidden_text" else DEFAULT_FORBIDDEN)
        if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
            config_errors.append(f"{key} must be a list of nonempty strings")
    if config_errors:
        raise ValueError("; ".join(config_errors))
    if not required:
        config_errors.append("required_text must include template questions and key content")
    missing = [t for t in required if normalize(t) not in full]
    forbidden = [t for t in requirements.get("forbidden_text", DEFAULT_FORBIDDEN) if normalize(t) in full]
    missing_urls = sorted(set(requirements.get("expected_urls", [])) - urls)
    source_errors = []
    sources = requirements.get("sources", [])
    if not sources:
        config_errors.append("sources must include source papers and template when provided")
    for item in sources:
        path = Path(item["path"])
        path = path if path.is_absolute() else base / path
        if not path.is_file():
            source_errors.append({"path": str(path), "error": "missing"})
        elif hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            source_errors.append({"path": str(path), "error": "hash mismatch"})
    expected = requirements.get("expected_pages")
    count_ok = bool(pages) and (expected is None or len(pages) == expected)
    auto = count_ok and not any([config_errors, missing, forbidden, missing_urls, source_errors])
    reviewed = visual.get("pages_reviewed", []) if isinstance(visual, dict) else []
    visual_ok = bool(isinstance(visual, dict) and visual.get("pdf_sha256") == digest
                     and isinstance(reviewed, list) and all(type(n) is int for n in reviewed)
                     and sorted(reviewed) == list(range(1, len(pages) + 1))
                     and visual.get("issues") == [])
    return {"pdf_sha256": digest, "pages": len(pages), "page_count_ok": count_ok,
            "configuration_errors": config_errors, "missing_text": missing,
            "forbidden_text_found": forbidden, "missing_urls": missing_urls,
            "actual_urls": sorted(urls), "source_errors": source_errors,
            "automatic_checks_passed": bool(auto), "visual_review_valid": visual_ok,
            "ready_for_delivery": bool(auto and visual_ok)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pdf")
    p.add_argument("--requirements", required=True)
    p.add_argument("--visual-review")
    p.add_argument("--report", required=True)
    a = p.parse_args()
    req_path, report_path = Path(a.requirements).resolve(), Path(a.report).resolve()
    protected = {Path(a.pdf).resolve(), req_path}
    if a.visual_review:
        protected.add(Path(a.visual_review).resolve())
    req = json.loads(req_path.read_text(encoding="utf-8"))
    for source in req.get("sources", []):
        path = Path(source["path"])
        protected.add((path if path.is_absolute() else req_path.parent / path).resolve())
    if report_path in protected:
        raise ValueError("Report path must not overwrite PDF, requirements, visual review, or sources.")
    visual = json.loads(Path(a.visual_review).read_text(encoding="utf-8")) if a.visual_review else None
    result = check(a.pdf, req, req_path.parent, visual)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready_for_delivery"] else (2 if result["automatic_checks_passed"] else 1)


if __name__ == "__main__":
    raise SystemExit(main())
