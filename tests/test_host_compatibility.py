from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "examples"))
import ndlib as nd
import skill_host as host
from run_demo import make_demo


class HostCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "中文 novel project"
        self.project.mkdir()

    def cli(self, script, *args, cwd=None):
        return subprocess.run([sys.executable, str(script), *map(str, args)], cwd=cwd,
                              capture_output=True, text=True, encoding="utf-8")

    def source_copy(self):
        root = self.root / "distribution"
        for name in host.RESOURCES:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        return root

    def test_documented_directory_routes_and_user_scopes(self):
        self.assertEqual(self.project / ".grok/skills" / host.NAME,
                         host.destination("grok", self.project, False))
        for name in ("antigravity", "antigravity-cli", "codex"):
            self.assertEqual(self.project / ".agents/skills" / host.NAME,
                             host.destination(name, self.project, False))
        with patch("skill_host.Path.home", return_value=self.project):
            self.assertEqual(self.project / ".gemini/config/skills" / host.NAME,
                             host.destination("antigravity", None, True))
            self.assertEqual(self.project / ".gemini/antigravity-cli/skills" / host.NAME,
                             host.destination("antigravity-cli", None, True))
        for project, user in ((None, False), (self.project, True)):
            with self.assertRaises(nd.Error):
                host.destination("grok", project, user)
        with self.assertRaises(nd.Error):
            host.destination("generic", None, True)
        with self.assertRaises(nd.Error):
            host.destination("unknown-cli", self.project, False)

    def test_every_layout_runs_copied_cli_and_original_demo_from_other_cwd(self):
        for name in host.HOSTS:
            with self.subTest(host=name):
                project = self.project / name
                project.mkdir()
                result = host.install(name, project)
                root = Path(result["installed"])
                self.assertTrue((root / "prompts/portable-start.md").is_file())
                self.assertTrue((root / "assets/novel-dna.schema.json").is_file())
                doctor = self.cli(root / "scripts/skill_host.py", "doctor", "--host", name,
                                  "--project", project, cwd=self.root)
                self.assertEqual(0, doctor.returncode, doctor.stderr)
                report = json.loads(doctor.stdout)
                self.assertTrue(report["toolchain_ready"])
                self.assertEqual([], report["different_or_missing_installed_resources"])
                self.assertEqual("not-run", report["host_runtime_test"])
                demo = self.cli(root / "examples/run_demo.py", "--out", project / "new-output", cwd=self.root)
                self.assertEqual(0, demo.returncode, demo.stderr)
                dna = nd.load_json(project / "new-output/novel-dna.json")
                self.assertEqual("reviewed", dna["status"])

    def test_install_preserves_existing_directories_and_project_instructions(self):
        instructions = self.project / "AGENTS.md"
        instructions.write_text("Existing project instructions", encoding="utf-8")
        target = host.destination("grok", self.project, False)
        target.mkdir(parents=True)
        sentinel = target / "keep.txt"
        sentinel.write_text("user file", encoding="utf-8")
        with self.assertRaisesRegex(nd.Error, "already exists"):
            host.install("grok", self.project)
        self.assertEqual("user file", sentinel.read_text())
        self.assertEqual("Existing project instructions", instructions.read_text())
        self.assertEqual([sentinel], list(target.iterdir()))

    def test_user_install_is_explicit_and_preserves_host_config(self):
        config = self.project / ".grok/config.toml"
        config.parent.mkdir()
        config.write_text('model = "custom"\n', encoding="utf-8")
        with patch("skill_host.Path.home", return_value=self.project):
            installed = host.install("grok", None, user=True)
        self.assertEqual(str(self.project / ".grok/skills" / host.NAME), installed["installed"])
        self.assertEqual('model = "custom"\n', config.read_text())

    def test_package_is_reproducible_and_every_resource_has_exact_hash(self):
        first, second = self.root / "first.zip", self.root / "second.zip"
        a = host.package("grok", first)
        b = host.package("grok", second)
        self.assertEqual(a["sha256"], b["sha256"])
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as archive:
            manifest = json.loads(archive.read(f"{host.NAME}/distribution.json"))
            self.assertEqual("grok", manifest["host"])
            self.assertEqual("not-run", manifest["host_runtime_test"])
            for path, sha in manifest["files"].items():
                self.assertEqual(sha, hashlib.sha256(archive.read(f"{host.NAME}/{path}")).hexdigest())
            self.assertEqual(set(manifest["files"]) | {"distribution.json"},
                             {p.removeprefix(host.NAME + "/") for p in archive.namelist()})
            self.assertTrue(all(".." not in Path(p).parts and not Path(p).is_absolute() for p in archive.namelist()))
        with self.assertRaisesRegex(nd.Error, "already exists"):
            host.package("grok", first)

    def test_unlisted_files_and_private_source_never_enter_package(self):
        source = self.source_copy()
        sentinel = ("PRIVATE SENTINEL " + self.root.name).encode("utf-8")
        for name in ("data/novel.txt", "workspaces/book/source.txt", "examples/private.txt",
                     ".env", ".git/config", "AGENTS.md", "scripts/private.py"):
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(sentinel)
        out = self.root / "clean.zip"
        host.package("antigravity", out, root=source)
        with zipfile.ZipFile(out) as archive:
            self.assertFalse(any(sentinel in archive.read(p) for p in archive.namelist()))

    def test_missing_resource_fails_before_creating_install(self):
        source = self.source_copy()
        (source / "assets/novel-dna.schema.json").unlink()
        with self.assertRaisesRegex(nd.Error, "Missing distribution"):
            host.install("grok", self.project, root=source)
        self.assertFalse((self.project / ".grok").exists())
        report = host.doctor("grok", root=source)
        self.assertFalse(report["toolchain_ready"])
        self.assertIn("assets/novel-dna.schema.json", report["missing_resources"])

    def test_doctor_is_read_only_and_does_not_execute_host(self):
        before = list(self.project.iterdir())
        with patch("skill_host.shutil.which", return_value="/example/grok"), \
             patch("subprocess.run", side_effect=AssertionError("host must not execute")):
            report = host.doctor("grok", self.project)
        self.assertEqual("not-checked", report["native_discovery"])
        self.assertEqual("missing", report["installation"])
        self.assertEqual(before, list(self.project.iterdir()))
        root = Path(host.install("grok", self.project)["installed"])
        (root / "scripts/ndlib.py").write_text("changed", encoding="utf-8")
        self.assertIn("scripts/ndlib.py", host.doctor("grok", self.project)["different_or_missing_installed_resources"])

    def test_symlinked_resource_and_install_parent_are_rejected(self):
        source = self.source_copy()
        original = source / "README.md"
        original.unlink()
        try:
            original.symlink_to(ROOT / "README.md")
            (self.project / ".grok").symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Host does not permit symlink creation.")
        with self.assertRaisesRegex(nd.Error, "symlink"):
            host.payload("grok", root=source)
        with self.assertRaisesRegex(nd.Error, "symlink"):
            host.install("grok", self.project)

    def test_host_cli_profiles_diagnostics_and_invalid_scope(self):
        for args in (("profiles",), ("doctor", "--host", "grok", "--project", self.project)):
            result = self.cli(ROOT / "scripts/skill_host.py", *args)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("not-run", json.loads(result.stdout)["host_runtime_test"])
        result = self.cli(ROOT / "scripts/skill_host.py", "install", "--host", "grok")
        self.assertEqual(2, result.returncode)

    def test_json_fence_import_is_explicit_and_preserves_quote_validation(self):
        make_demo(self.root / "demo")
        work = self.root / "demo/workspace"
        record = nd.load_json(work / "analyses/C000001.json")
        reply = self.root / "reply.md"
        reply.write_bytes(("\ufeff```json\r\n" + json.dumps(record, ensure_ascii=False, indent=2).replace("\n", "\r\n") + "\r\n```\r\n").encode("utf-8"))
        with self.assertRaises(nd.Error):
            nd.load_json(reply)
        self.assertEqual(record, nd.load_json(reply, allow_fence=True))
        (work / "analyses/C000001.json").unlink()
        imported = self.cli(ROOT / "scripts/novel_distill.py", "record", work, "--analysis", reply, "--from-chat")
        self.assertEqual(0, imported.returncode, imported.stderr)
        record["observations"][0]["evidence"][0]["quote"] = "fabricated"
        reply.write_text("```json\n" + json.dumps(record) + "\n```", encoding="utf-8")
        bad = self.cli(ROOT / "scripts/novel_distill.py", "record", work, "--analysis", reply, "--from-chat", "--replace")
        self.assertEqual(2, bad.returncode)
        self.assertIn("exactly match", bad.stderr)
        self.assertNotEqual("fabricated", nd.load_json(work / "analyses/C000001.json")["observations"][0]["evidence"][0]["quote"])

    def test_fence_adapter_rejects_prose_multiple_objects_duplicates_and_nonfinite(self):
        reply = self.root / "reply.md"
        for text in ('前言\n```json\n{}\n```', '```json\n{}\n```\n后记',
                     '```json\n{}\n```\n```json\n{}\n```', '```json\n{"x":1,"x":2}\n```',
                     '```json\n{"x":NaN}\n```', '```json\n{"x":Infinity}\n```'):
            reply.write_text(text, encoding="utf-8")
            with self.subTest(reply=text), self.assertRaises(nd.Error):
                nd.load_json(reply, allow_fence=True)

    def test_quote_file_keeps_exact_unicode_whitespace_and_shell_metacharacters(self):
        quote = '她说：“$HOME `whoami` \'别动\'。”\n😀'
        source = self.root / "novel.txt"
        source.write_bytes(("第一章 测试\n" + quote + "\n").encode("utf-8"))
        work = self.root / "quote-work"
        nd.prepare(source, work, "quote", "utf-8", 6000, 300)
        qfile = self.root / "quote.txt"
        qfile.write_bytes(quote.encode("utf-8"))
        located = self.cli(ROOT / "scripts/novel_distill.py", "locate", work, "--id", "C000001", "--quote-file", qfile)
        self.assertEqual(0, located.returncode, located.stderr)
        match = json.loads(located.stdout)["matches"][0]
        self.assertEqual(quote, match["quote"])
        self.assertTrue(match["can_record"])
        qfile.write_bytes(("\ufeff" + quote.replace("\n", "\r\n")).encode("utf-8"))
        located = self.cli(ROOT / "scripts/novel_distill.py", "locate", work, "--quote-file", qfile)
        self.assertEqual(quote, json.loads(located.stdout)["matches"][0]["quote"])
        qfile.write_bytes((quote + "\nextra").encode("utf-8"))
        located = self.cli(ROOT / "scripts/novel_distill.py", "locate", work, "--quote-file", qfile)
        self.assertEqual(0, json.loads(located.stdout)["total_matches"])

    def test_packaged_copy_works_after_extraction(self):
        archive = self.root / "generic.zip"
        host.package("generic", archive)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(self.project)
        root = self.project / host.NAME
        result = self.cli(root / "scripts/novel_distill.py", "--version", cwd=self.root)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(nd.VERSION, result.stdout.strip())

    def test_host_smoke_command_resolves_relative_output_before_switching_cwd(self):
        result = self.cli(ROOT / "examples/run_host_demo.py", "--out", "outputs/relative 中文", cwd=self.project)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(set(host.HOSTS), {item["host"] for item in report["layouts"]})
        output = self.project / "outputs/relative 中文"
        self.assertTrue((output / "host-check.json").is_file())
        self.assertTrue((output / "grok 中文 project/demo/novel-dna.json").is_file())


if __name__ == "__main__":
    unittest.main()
