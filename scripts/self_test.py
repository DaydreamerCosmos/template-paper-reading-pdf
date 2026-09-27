"""Behavioral checks using synthetic documents only; no private fixtures."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from pypdf import PdfWriter
from pypdf.annotations import Link
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from extract_sources import extract
from prepare_template import prepare
from verify_pdf import check


def pdf_fixture(path):
    writer = PdfWriter()
    page = writer.add_blank_page(595, 842)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 72 720 Td (Question one 0.7962) Tj ET")
    page[NameObject("/Contents")] = stream
    writer.add_annotation(0, Link(rect=(72, 690, 200, 710), url="https://example.org/paper"))
    writer.write(path)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paper = self.root / "paper.pdf"
        pdf_fixture(self.paper)
        self.digest = hashlib.sha256(self.paper.read_bytes()).hexdigest()
        self.req = {"required_text": ["Question one", "0.7962"],
                    "expected_urls": ["https://example.org/paper"],
                    "sources": [{"path": "paper.pdf", "sha256": self.digest}], "expected_pages": 1}
        self.visual = {"pdf_sha256": self.digest, "pages_reviewed": [1], "issues": []}

    def test_visual_gate_and_success(self):
        result = check(self.paper, self.req, self.root)
        self.assertTrue(result["automatic_checks_passed"])
        self.assertFalse(result["ready_for_delivery"])
        self.assertTrue(check(self.paper, self.req, self.root, self.visual)["ready_for_delivery"])

    def test_stale_or_incomplete_review_rejected(self):
        for change in [{"pdf_sha256": "0" * 64}, {"pages_reviewed": []},
                       {"pages_reviewed": [1, 1]}, {"issues": ["clipped table"]}]:
            self.assertFalse(check(self.paper, self.req, self.root, self.visual | change)["ready_for_delivery"])

    def test_text_link_source_and_watermark_failures(self):
        cases = [{"required_text": ["missing paragraph"]}, {"expected_urls": ["https://example.org/missing"]},
                 {"sources": [{"path": "paper.pdf", "sha256": "0" * 64}]},
                 {"forbidden_text": ["Question one"]}, {"expected_pages": 2}, {"required_text": []}]
        for change in cases:
            self.assertFalse(check(self.paper, self.req | change, self.root, self.visual)["automatic_checks_passed"])

    def test_precise_watermark_removal_and_source_integrity(self):
        original = self.root / "source.docx"
        body = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Keep the question</w:t></w:r></w:p></w:body></w:document>'
        header = '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:v="urn:schemas-microsoft-com:vml"><w:p><w:r><w:t>Keep header</w:t><w:pict><v:shape id="watermark"><v:textpath string="James科研小班课"/></v:shape><v:shape id="other"><v:textpath string="Approved mark"/></v:shape></w:pict></w:r></w:p></w:hdr>'.encode("utf-8")
        with ZipFile(original, "w") as z:
            z.writestr("word/document.xml", body)
            z.writestr("word/header1.xml", header)
            z.writestr("customXml/item1.xml", b"preserve-me")
        old = original.read_bytes()
        dest = self.root / "clean.docx"
        report = prepare(original, dest)
        self.assertEqual(report["removed_shapes"], 1)
        self.assertEqual(original.read_bytes(), old)
        with ZipFile(dest) as z:
            self.assertEqual(z.read("word/document.xml"), body)
            self.assertEqual(z.read("customXml/item1.xml"), b"preserve-me")
            h = z.read("word/header1.xml")
            self.assertNotIn("James科研小班课".encode(), h)
            self.assertIn(b"Approved mark", h)
            self.assertIn(b"Keep header", h)
        with self.assertRaises(ValueError):
            prepare(original, original)
        with self.assertRaises(FileExistsError):
            prepare(original, dest)
        no_match = prepare(original, self.root / "unmatched.docx", ["Absent phrase"])
        self.assertEqual(no_match["removed_shapes"], 0)
        evidence = extract([self.paper], original, self.root / "evidence")
        self.assertEqual(evidence[0]["pages"], 1)
        self.assertEqual(evidence[1]["sha256"], hashlib.sha256(old).hexdigest())
        with self.assertRaises(FileExistsError):
            extract([self.paper], original, self.root / "evidence")

    def test_cli_exit_codes_and_output_protection(self):
        req = self.root / "requirements.json"
        visual = self.root / "visual.json"
        req.write_text(json.dumps(self.req), encoding="utf-8")
        visual.write_text(json.dumps(self.visual), encoding="utf-8")
        cmd = [sys.executable, str(Path(__file__).with_name("verify_pdf.py")), str(self.paper),
               "--requirements", str(req), "--report", str(self.root / "report.json")]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)
        self.assertEqual(subprocess.run(cmd + ["--visual-review", str(visual)], capture_output=True).returncode, 0)
        before = self.paper.read_bytes()
        bad = cmd[:-1] + [str(self.paper)]
        self.assertNotEqual(subprocess.run(bad, capture_output=True).returncode, 0)
        self.assertEqual(self.paper.read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
