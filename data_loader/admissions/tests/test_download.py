import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from admissions.download import install


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="olympguide-download-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.archive = self.root / "snapshot.zip"
        self.manifest = self.root / "manifest.json"
        self.target = self.root / "installed"

    def prepare(self, files=None):
        files = files or {"catalog.json": b'{"rules": []}', "sources/document.pdf": b"%PDF-fixture"}
        with zipfile.ZipFile(self.archive, "w") as bundle:
            for name, data in files.items():
                bundle.writestr(name, data)
        metadata = lambda data: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        manifest = {"schema_version": 1, "admission_year": 2026,
                    "archive": {"url": "https://github.com/example/data.zip", **metadata(self.archive.read_bytes())},
                    "files": [{"path": name, **metadata(data)} for name, data in files.items()]}
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest

    def run_install(self):
        return install(manifest_path=self.manifest, archive=self.archive, target=self.target)

    def test_install_and_repeat_without_archive_or_network(self):
        self.prepare()
        self.assertEqual(self.run_install(), self.target)
        self.assertEqual((self.target / "sources/document.pdf").read_bytes(), b"%PDF-fixture")
        self.archive.unlink()
        with patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected network access")):
            self.assertEqual(install(manifest_path=self.manifest, target=self.target), self.target)

    def test_corrupted_archive_does_not_install(self):
        self.prepare()
        self.archive.write_bytes(self.archive.read_bytes() + b"corruption")
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertFalse(self.target.exists())

    def test_incorrect_file_digest_does_not_install(self):
        manifest = self.prepare()
        manifest["files"][0]["sha256"] = "0" * 64
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertFalse(self.target.exists())

    def test_missing_manifest_file_does_not_install(self):
        manifest = self.prepare()
        manifest["files"].pop()
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertFalse(self.target.exists())

    def test_unsafe_paths_and_case_collisions_are_rejected(self):
        for names in [("../outside",), ("C:/outside",), ("a\\outside",),
                      ("/outside",), ("a//b",), ("Catalog.json", "catalog.json")]:
            with self.subTest(names=names):
                self.prepare({name: b"data" for name in names})
                with self.assertRaises(ValueError):
                    self.run_install()
                self.assertFalse(self.target.exists())
        self.assertFalse((self.root / "outside").exists())

    def test_existing_modified_snapshot_is_preserved(self):
        self.prepare()
        self.run_install()
        path = self.target / "catalog.json"
        path.write_bytes(b"local edit")
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertEqual(path.read_bytes(), b"local edit")

    def test_network_failure_does_not_leave_installed_snapshot(self):
        self.prepare()
        with patch("urllib.request.urlopen", side_effect=OSError("network unavailable")):
            with self.assertRaises(OSError):
                install(manifest_path=self.manifest, target=self.target)
        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.root.glob(".admissions-*")), [])
