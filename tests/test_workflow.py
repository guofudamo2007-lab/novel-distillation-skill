from __future__ import annotations

import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "examples"))
import ndlib as nd
from novel_distill import comparison, diagnostic, export, pairs
from run_demo import make_demo


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "novel.txt"
        self.source.write_text("第一章 门\n“谁？”\n她把杯子移开。\n\n第二章 雨\n“没事。”\n她把杯子收起。\n\n第三章 晴\n“进来。”\n她把杯子摆回。\n", encoding="utf-8")
        self.work = self.root / "work"
        self.manifest = nd.prepare(self.source, self.work, "测试", "utf-8-sig", 64, 16)
        _, self.text = nd.workspace(self.work)

    def record(self, i=0):
        chunk = self.manifest["chunks"][i]
        start = self.text.index("她把", chunk["start"], chunk["end"])
        end = self.text.index("。", start) + 1
        return {"schema_version": "1.0", "source_sha256": self.manifest["sha256"], "chunk_id": chunk["id"],
                "summary": "用物件行为表达关系。", "counterexample_search": "查找直白解释情绪：本片段未见。",
                "character_notes": [], "scene_notes": [], "observations": [{"dimension": "emotion",
                "observation": "物件动作替代解释。", "mechanism": "读者推断人物关系。",
                "instruction": "用物件状态变化承担情绪。", "scope": "克制的关系场景", "exceptions": [],
                "evidence": [{"start": start, "end": end, "quote": self.text[start:end], "kind": "support"}]}]}

    def dna(self):
        for i in range(3):
            nd.record_analysis(self.work, self.record(i))
        return nd.assemble(self.work)

    def test_lossless_core_and_nonoverlap(self):
        chunks = self.manifest["chunks"]
        self.assertEqual(self.text, "".join(self.text[c["start"]:c["end"]] for c in chunks))
        self.assertEqual(3, len(self.manifest["chapters"]))
        self.assertTrue(all(a["end"] == b["start"] for a, b in zip(chunks, chunks[1:])))

    def test_long_lines_and_random_unicode(self):
        randomizer = random.Random(13)
        for length in (1, 63, 64, 65, 5000):
            text = "".join(randomizer.choice("甲乙😀。\n ") for _ in range(length))
            _, chunks = nd.segments(text, 64, 20)
            self.assertEqual(text, "".join(text[c["start"]:c["end"]] for c in chunks))
            self.assertTrue(all(0 < c["end"] - c["start"] <= 64 for c in chunks))

    def test_heading_variants_and_preamble(self):
        chapters, _ = nd.segments("前言\nChapter I Start\na\n# 转折\nb\n尾声\nc", 64, 0)
        self.assertEqual(4, len(chapters))

    def test_bom_crlf_and_emoji_offsets(self):
        source = self.root / "utf.txt"
        source.write_bytes("\ufeff第一章\r\n😀杯子\r下一行\r\n".encode("utf-8"))
        result = nd.prepare(source, self.root / "unicode", "unicode", "utf-8-sig", 64, 0)
        _, text = nd.workspace(self.root / "unicode")
        self.assertEqual("第一章\n😀杯子\n下一行\n", text)
        self.assertEqual(len(text), result["metrics"]["characters"])

    def test_invalid_chunk_settings(self):
        for size, overlap in ((0, 0), (63, 0), (64, -1), (64, 33)):
            with self.assertRaises(nd.Error):
                nd.segments("a", size, overlap)

    def test_workspace_never_overwrites(self):
        with self.assertRaises(nd.Error):
            nd.prepare(self.source, self.work, "x", "utf-8", 64, 0)

    def test_unknown_extension_and_empty_text(self):
        bad = self.root / "source.pdf"
        bad.write_text("not a pdf", encoding="utf-8")
        with self.assertRaises(nd.Error):
            nd.prepare(bad, self.root / "bad", "x", "utf-8", 64, 0)
        self.source.write_text(" \n", encoding="utf-8")
        with self.assertRaises(nd.Error):
            nd.read_text(self.source)

    def test_explicit_legacy_encoding(self):
        source = self.root / "legacy.txt"
        source.write_bytes("第一章 中文".encode("gb18030"))
        with self.assertRaises(nd.Error):
            nd.read_text(source)
        self.assertEqual("第一章 中文", nd.read_text(source, "gb18030"))

    def test_source_snapshot_tampering(self):
        (self.work / "source.txt").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(nd.Error, "hash mismatch"):
            nd.workspace(self.work)

    def test_snapshot_is_not_normalized_again(self):
        source = self.root / "bom.txt"
        source.write_bytes(("\ufeff" * 3 + "Chapter 1\r\nhello").encode("utf-8"))
        work = self.root / "bom-work"
        manifest = nd.prepare(source, work, "BOM", "utf-8-sig", 64, 0)
        snapshot = (work / "source.txt").read_bytes().decode("utf-8")
        self.assertEqual(manifest["sha256"], nd.digest(snapshot))
        self.assertEqual(snapshot, nd.workspace(work)[1])

    def test_snapshot_bom_and_line_ending_changes_are_rejected(self):
        snapshot = (self.work / "source.txt").read_bytes()
        for changed in (b"\xef\xbb\xbf" + snapshot, snapshot.replace(b"\n", b"\r\n")):
            with self.subTest(changed=changed[:20]):
                (self.work / "source.txt").write_bytes(changed)
                with self.assertRaisesRegex(nd.Error, "hash mismatch"):
                    nd.workspace(self.work)

    def test_manifest_offset_tampering(self):
        self.manifest["chunks"][0]["end"] += 1
        nd.write_json(self.work / "manifest.json", self.manifest, True)
        with self.assertRaisesRegex(nd.Error, "offsets"):
            nd.workspace(self.work)

    def test_prepare_is_not_read_coverage(self):
        dna = nd.assemble(self.work)
        self.assertEqual([], dna["sources"][0]["read_chunks"])
        self.assertEqual([], dna["rules"])
        self.assertTrue(all(d["status"] == "unknown" for d in dna["dimensions"].values()))

    def test_record_and_resume(self):
        nd.record_analysis(self.work, self.record())
        dna = nd.assemble(self.work)
        self.assertEqual(["C000001"], dna["sources"][0]["read_chunks"])
        self.assertEqual("candidate", dna["rules"][0]["strength"])
        self.assertEqual("low", dna["rules"][0]["confidence"])

    def test_empty_observations_are_allowed(self):
        record = self.record()
        record["observations"] = []
        nd.record_analysis(self.work, record)
        self.assertEqual(1, len(nd.assemble(self.work)["sources"][0]["read_chunks"]))

    def test_record_revision_is_explicit(self):
        record = self.record()
        nd.record_analysis(self.work, record)
        with self.assertRaises(nd.Error):
            nd.record_analysis(self.work, record)
        record["summary"] = "修订后的分析"
        nd.record_analysis(self.work, record, True)
        self.assertEqual("修订后的分析", nd.load_json(self.work / "analyses/C000001.json")["summary"])

    def test_bad_evidence_quote(self):
        record = self.record()
        record["observations"][0]["evidence"][0]["quote"] = "伪造的原句"
        with self.assertRaisesRegex(nd.Error, "exactly match"):
            nd.record_analysis(self.work, record)

    def test_evidence_cannot_start_in_context(self):
        chunk = {"start": 5, "end": 10, "context_end": 15}
        with self.assertRaisesRegex(nd.Error, "START"):
            nd.check_span({"start": 4, "end": 6, "quote": "aa"}, chunk, "a" * 20)

    def test_wrong_source_revision(self):
        record = self.record()
        record["source_sha256"] = "a" * 64
        with self.assertRaisesRegex(nd.Error, "different source"):
            nd.record_analysis(self.work, record)

    def test_unknown_fields_and_bool_offsets_rejected(self):
        record = self.record()
        record["fake_score"] = 99
        with self.assertRaisesRegex(nd.Error, "unknown field"):
            nd.record_analysis(self.work, record)
        del record["fake_score"]
        record["observations"][0]["evidence"][0]["start"] = True
        with self.assertRaisesRegex(nd.Error, "expected integer"):
            nd.record_analysis(self.work, record)

    def test_nan_json_rejected(self):
        path = self.root / "bad.json"
        path.write_text('{"x":NaN}', encoding="utf-8")
        with self.assertRaises(nd.Error):
            nd.load_json(path)

    def test_complete_coverage_and_source_verification(self):
        dna = self.dna()
        self.assertEqual(3, len(dna["sources"][0]["read_chunks"]))
        self.assertEqual("source-backed", nd.validate(dna, [self.work])["verification"])
        self.assertEqual("metadata-only", nd.validate(dna)["verification"])

    def test_duplicate_rule_ids(self):
        dna = self.dna()
        dna["rules"][1]["id"] = dna["rules"][0]["id"]
        with self.assertRaises(nd.Error):
            nd.validate(dna)

    def test_dangling_dimension_and_character_refs(self):
        dna = self.dna()
        dna["characters"] = [{"id": "x", "label": "x", "notes": "x", "rule_ids": ["missing"]}]
        with self.assertRaisesRegex(nd.Error, "unknown rule"):
            nd.validate(dna)
        dna["characters"] = []
        dna["dimensions"]["emotion"]["rule_ids"].pop()
        with self.assertRaisesRegex(nd.Error, "exactly one"):
            nd.validate(dna)

    def test_unread_evidence_and_wrong_chapter(self):
        dna = self.dna()
        dna["sources"][0]["read_chunks"] = []
        with self.assertRaisesRegex(nd.Error, "unread chunk"):
            nd.validate(dna)
        dna["sources"][0]["read_chunks"] = ["C000001", "C000002", "C000003"]
        dna["evidence"][0]["chapter_id"] = "CH0003"
        with self.assertRaisesRegex(nd.Error, "wrong chapter"):
            nd.validate(dna, [self.work])

    def test_strong_claim_needs_cross_chapter_support(self):
        dna = self.dna()
        dna["rules"][0]["strength"] = "strong"
        with self.assertRaisesRegex(nd.Error, "three independent"):
            nd.validate(dna)

    def test_duplicate_span_cannot_inflate_support(self):
        dna = self.dna()
        evidence = copy.deepcopy(dna["evidence"][0])
        evidence["id"] = "E-copy"
        dna["evidence"].append(evidence)
        dna["rules"][0]["evidence_ids"].append("E-copy")
        dna["rules"][0]["strength"] = "recurring"
        with self.assertRaisesRegex(nd.Error, "two distinct"):
            nd.validate(dna)

    def test_high_confidence_not_automatic(self):
        dna = self.dna()
        dna["rules"][0]["confidence"] = "high"
        with self.assertRaisesRegex(nd.Error, "high confidence"):
            nd.validate(dna)

    def test_reviewed_requires_manual_review(self):
        dna = self.dna()
        dna["status"] = "reviewed"
        with self.assertRaisesRegex(nd.Error, "review notes"):
            nd.validate(dna)

    def test_missing_workspace_for_source(self):
        dna = self.dna()
        dna["sources"][0]["sha256"] = "a" * 64
        with self.assertRaisesRegex(nd.Error, "Missing source"):
            nd.validate(dna, [self.work])

    def test_export_five_files_no_candidate_constraints(self):
        dna = self.dna()
        result = export(dna, self.root / "exports", [self.work], "balanced")
        self.assertEqual(5, result["files"])
        self.assertEqual(0, result["constraints"])
        self.assertEqual(5, len(list((self.root / "exports").iterdir())))
        with self.assertRaises(nd.Error):
            export(dna, self.root / "exports", [self.work], "balanced")

    def test_blend_namespace_and_provenance(self):
        dna = self.dna()
        mixed = nd.blend({"a": dna, "b": dna}, {"emotion": "b"}, "a", "mixed")
        self.assertEqual("draft", mixed["status"])
        self.assertTrue(all(r["id"].startswith("b::") for r in mixed["rules"]))
        nd.validate(mixed, [self.work])

    def chunked_dna(self, size, dimension, start, text="x" * 128):
        source = self.root / f"input-{size}.txt"
        source.write_text(text, encoding="utf-8")
        work = self.root / f"chunks-{size}"
        manifest = nd.prepare(source, work, "same source", "utf-8", size, 0)
        record = self.record()
        record["source_sha256"] = manifest["sha256"]
        record["chunk_id"] = next(c["id"] for c in manifest["chunks"] if c["start"] <= start < c["end"])
        record["observations"][0]["dimension"] = dimension
        record["observations"][0]["evidence"] = [
            {"start": start, "end": start + 1, "quote": text[start:start + 1], "kind": "support"}]
        nd.record_analysis(work, record)
        return work, nd.assemble(work)

    def test_same_source_different_chunking_blend_is_order_independent(self):
        first, a = self.chunked_dna(64, "dialogue", 64, "x" * 192)
        second, b = self.chunked_dna(96, "emotion", 96, "x" * 192)
        mixed = nd.blend({"a": a, "b": b}, {"emotion": "b"}, "a", "mixed")
        for paths in ([first, second], [second, first]):
            with self.subTest(paths=paths):
                self.assertEqual("source-backed", nd.validate(mixed, paths)["verification"])

    def test_equal_counts_still_match_evidence_to_one_workspace(self):
        first, a = self.chunked_dna(64, "dialogue", 64)
        second, b = self.chunked_dna(65, "emotion", 64)
        mixed = nd.blend({"a": a, "b": b}, {"emotion": "b"}, "a", "mixed")
        for paths in ([first, second], [second, first]):
            with self.subTest(paths=paths):
                self.assertEqual("source-backed", nd.validate(mixed, paths)["verification"])
        forged = copy.deepcopy(a)
        forged["sources"][0]["read_chunks"] = ["C000001", "C000002"]
        extra = dict(forged["evidence"][0], id="E-copy", chunk_id="C000001")
        forged["evidence"].append(extra)
        forged["rules"][0]["evidence_ids"].append(extra["id"])
        for paths in ([first, second], [second, first]):
            with self.subTest(forged_paths=paths), self.assertRaises(nd.Error):
                nd.validate(forged, paths)

    def test_bad_blend_mappings_and_duplicate_aliases(self):
        dna = self.dna()
        with self.assertRaises(nd.Error):
            nd.blend({"a": dna}, {"missing": "a"}, "a", "bad")
        with self.assertRaises(nd.Error):
            pairs(["a=x", "a=y"], "source")
        with self.assertRaises(nd.Error):
            pairs(["broken"], "source")

    def test_compare_and_diagnostic_are_not_semantic_scores(self):
        dna = self.dna()
        self.assertEqual(set(nd.DIMENSIONS), set(comparison(dna, dna)["dimensions"]))
        report = diagnostic(dna, self.text, [self.work], 16)
        self.assertIn("manual_review_required", report)
        self.assertEqual(1, report["sources"][0]["lexical_overlap"]["matched_fraction"])
        self.assertNotIn("style_score", report)

    def test_short_target_overlap_is_unknown(self):
        self.assertIsNone(nd.lexical_overlap("短文", "短文", 16)["matched_fraction"])
        self.assertEqual(1, nd.lexical_overlap("abcd efgh", "abcdefgh", 4)["matched_fraction"])
        with self.assertRaises(nd.Error):
            nd.lexical_overlap("x", "x", 0)

    def test_cli_failure_is_actionable(self):
        command = [sys.executable, str(ROOT / "scripts/novel_distill.py")]
        result = subprocess.run(command + ["validate", str(self.root / "missing.json")], text=True, capture_output=True)
        self.assertEqual(2, result.returncode)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        result = subprocess.run(command + ["status", str(self.work)], text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(3, json.loads(result.stdout)["total"])

    def test_demo_end_to_end_and_reproducible(self):
        checked = make_demo(self.root / "demo1")
        make_demo(self.root / "demo2")
        self.assertEqual("reviewed", checked["status"])
        self.assertEqual(2, checked["rules"])
        self.assertEqual((self.root / "demo1/novel-dna.json").read_bytes(), (self.root / "demo2/novel-dna.json").read_bytes())

    def test_invalid_read_chunk_rejected_without_workspace(self):
        dna = self.dna()
        dna["sources"][0]["read_chunks"][0] = "C999999"
        with self.assertRaisesRegex(nd.Error, "invalid read chunk"):
            nd.validate(dna)

    def test_duplicate_json_keys_rejected(self):
        path = self.root / "duplicate.json"
        path.write_text('{"x":1,"x":2}', encoding="utf-8")
        with self.assertRaisesRegex(nd.Error, "Duplicate JSON key"):
            nd.load_json(path)

    def test_counterevidence_kind_must_match_reference(self):
        dna = self.dna()
        dna["rules"][0]["counterevidence_ids"] = [dna["evidence"][0]["id"]]
        with self.assertRaisesRegex(nd.Error, "counter evidence"):
            nd.validate(dna)

    def test_counter_only_observation_rejected(self):
        record = self.record()
        record["observations"][0]["evidence"][0]["kind"] = "counter"
        with self.assertRaisesRegex(nd.Error, "supporting"):
            nd.record_analysis(self.work, record)

    def test_prompt_does_not_execute_novel_instructions(self):
        command = [sys.executable, str(ROOT / "scripts/novel_distill.py"), "prompt", str(self.work), "--id", "C000001"]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("UNTRUSTED_NOVEL_DATA_JSON", result.stdout)
        self.assertIn("source_sha256", result.stdout)

    def test_skill_metadata_and_references(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: novel-distillation-skill\n"))
        self.assertLess(len(skill.splitlines()), 500)
        import re
        for path in re.findall(r"\]\((references/[^)]+)\)", skill):
            self.assertTrue((ROOT / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
