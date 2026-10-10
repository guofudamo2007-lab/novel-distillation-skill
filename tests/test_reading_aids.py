from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "examples"))
import ndlib as nd
from ndtools import (check_recipe, locate_quote, make_recipe, quick_status,
                     reading_memory, record_memory, record_template)
from run_demo import make_demo
from run_evaluation import prepare_evaluation


class ReadingAidsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        make_demo(self.root / "demo")
        self.work = self.root / "demo/workspace"
        self.dna = nd.load_json(self.root / "demo/novel-dna.json")
        self.manifest, self.text = nd.workspace(self.work)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts/novel_distill.py"), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8")

    def memory_entry(self, mid="M000002", index=1, kind="character", stage="state"):
        chunk = self.manifest["chunks"][index]
        quote = self.text[chunk["start"]:chunk["start"] + 10]
        span = {"chunk_id": chunk["id"], "start": chunk["start"], "end": chunk["start"] + len(quote), "quote": quote}
        return {"schema_version": "1.0", "source_sha256": self.manifest["sha256"],
                "id": mid, "kind": kind, "stage": stage, "subject": "周闻", "summary": "局部记录",
                "certainty": "inferred", "evidence": [span], "related_ids": []}

    def test_memory_never_adds_read_coverage(self):
        before = nd.assemble(self.work)["sources"][0]["read_chunks"]
        record_memory(self.work, self.memory_entry())
        self.assertEqual(before, nd.assemble(self.work)["sources"][0]["read_chunks"])

    def test_memory_requires_exact_quotes_and_recorded_chunks(self):
        entry = self.memory_entry()
        entry["evidence"][0]["quote"] = "假的原句"
        with self.assertRaisesRegex(nd.Error, "exactly match"):
            record_memory(self.work, entry)
        (self.work / "analyses/C000002.json").unlink()
        with self.assertRaisesRegex(nd.Error, "recorded analysis"):
            record_memory(self.work, self.memory_entry())

    def test_memory_wrong_revision_and_filename_are_rejected(self):
        entry = self.memory_entry()
        entry["source_sha256"] = "a" * 64
        with self.assertRaisesRegex(nd.Error, "different source"):
            record_memory(self.work, entry)
        (self.work / "memory/M000001.json").rename(self.work / "memory/M000002.json")
        with self.assertRaisesRegex(nd.Error, "filenames"):
            reading_memory(self.work)

    def test_memory_evidence_limit_and_future_related_entries(self):
        entry = self.memory_entry()
        entry["evidence"] = [dict(entry["evidence"][0], quote=self.text[entry["evidence"][0]["start"]:entry["evidence"][0]["start"] + n],
                                  end=entry["evidence"][0]["start"] + n) for n in range(1, 8)]
        with self.assertRaisesRegex(nd.Error, "too many"):
            record_memory(self.work, entry)
        record_memory(self.work, self.memory_entry())
        earlier = self.memory_entry("M000003", index=0)
        earlier["related_ids"] = ["M000002"]
        with self.assertRaisesRegex(nd.Error, "occurs after"):
            record_memory(self.work, earlier)

    def test_memory_is_append_only_and_no_future_context(self):
        with self.assertRaisesRegex(nd.Error, "sequential"):
            record_memory(self.work, self.memory_entry("M000001"))
        record_memory(self.work, self.memory_entry())
        self.assertEqual([], reading_memory(self.work, "C000001")["entries"])
        self.assertEqual(["M000001"], [e["id"] for e in reading_memory(self.work, "C000002")["entries"]])
        self.assertEqual(2, reading_memory(self.work, "C000003")["eligible"])

    def test_memory_bounds_and_exact_subject_filter(self):
        entry = self.memory_entry()
        entry["summary"] = "长" * 800
        record_memory(self.work, entry)
        context = reading_memory(self.work, budget=600, limit=1)
        self.assertLessEqual(len(json.dumps(context["entries"], ensure_ascii=False)), 600)
        self.assertEqual(1, len(context["entries"]))
        self.assertEqual(1, context["omitted"])
        self.assertEqual([], reading_memory(self.work, subjects=["不存在的人物"])["entries"])
        with self.assertRaises(nd.Error):
            reading_memory(self.work, budget=0)

    def test_foreshadow_payoff_requires_linked_setup(self):
        entry = self.memory_entry(kind="foreshadow", stage="payoff")
        with self.assertRaisesRegex(nd.Error, "prior plant"):
            record_memory(self.work, entry)
        entry["stage"] = "plant"
        record_memory(self.work, entry)
        payoff = self.memory_entry("M000003", 2, "foreshadow", "payoff")
        payoff["related_ids"] = ["M000002"]
        record_memory(self.work, payoff)
        self.assertEqual("payoff", reading_memory(self.work)["entries"][0]["stage"])

    def test_memory_unknown_links_and_wrong_kind_are_rejected(self):
        entry = self.memory_entry()
        entry["related_ids"] = ["M999999"]
        with self.assertRaisesRegex(nd.Error, "unknown"):
            record_memory(self.work, entry)
        entry["related_ids"] = []
        entry["stage"] = "payoff"
        with self.assertRaisesRegex(nd.Error, "disagree"):
            record_memory(self.work, entry)

    def test_memory_symlink_is_rejected(self):
        target = self.root / "entry.json"
        target.write_text("{}", encoding="utf-8")
        try:
            (self.work / "memory/M000002.json").symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("This host does not grant symlink creation privileges.")
        with self.assertRaisesRegex(nd.Error, "symlinks"):
            reading_memory(self.work)

    def test_quote_location_repetition_and_unicode(self):
        quote = "空杯"
        result = locate_quote(self.work, quote, limit=1)
        self.assertTrue(result["ambiguous"])
        self.assertTrue(result["truncated"])
        for match in locate_quote(self.work, quote)["matches"]:
            self.assertEqual(quote, self.text[match["start"]:match["end"]])
            self.assertTrue(match["can_record"])
        self.assertEqual(0, locate_quote(self.work, "不存在😀")["total_matches"])
        unique = locate_quote(self.work, "她没有回头。", "C000001")
        self.assertEqual(1, unique["total_matches"])
        with self.assertRaises(nd.Error):
            locate_quote(self.work, "")

    def test_quote_crossing_core_or_chapter_is_marked(self):
        source = self.root / "long.txt"
        source.write_text("😀" + "甲" * 63 + "乙" * 64, encoding="utf-8")
        work = self.root / "long-work"
        nd.prepare(source, work, "x", "utf-8", 64, 4)
        match = locate_quote(work, "甲乙乙", "C000001")["matches"][0]
        self.assertEqual(63, match["start"])
        self.assertTrue(match["can_record"])
        self.assertFalse(locate_quote(work, "甲" + "乙" * 8)["matches"][0]["can_record"])
        self.assertEqual(0, locate_quote(work, "乙乙", "C000001")["total_matches"])

    def test_template_is_not_valid_analysis_or_coverage(self):
        template = record_template(self.work, "C000002")
        with self.assertRaises(nd.Error):
            nd.check_record(template, self.manifest, self.text)
        self.assertEqual(self.manifest["sha256"], template["source_sha256"])

    def test_quick_status_does_not_read_source_or_analysis(self):
        original = nd.load_json
        def manifest_only(path):
            self.assertEqual("manifest.json", path.name)
            return original(path)
        with patch("ndtools.load_json", side_effect=manifest_only), patch("ndtools.workspace", side_effect=AssertionError):
            result = quick_status(self.work)
        self.assertEqual("not-verified", result["verification"])
        self.assertNotIn("recorded", result)
        self.assertEqual(3, result["record_files_present"])
        (self.work / "analyses/C000001.json").write_text("bad", encoding="utf-8")
        self.assertEqual(3, quick_status(self.work)["record_files_present"])
        with self.assertRaises(nd.Error):
            nd.assemble(self.work)

    def test_quick_status_rejects_traversal_ids_and_malformed_manifest(self):
        for chunks in ([{"id": "../escape"}], ["invalid"], [], [{"id": "C000001"}, {"id": "C000001"}]):
            malformed = dict(self.manifest, chunks=chunks)
            nd.write_json(self.work / "manifest.json", malformed, True)
            with self.subTest(chunks=chunks), self.assertRaises(nd.Error):
                quick_status(self.work)

    def test_new_rules_cannot_promote_without_per_rule_review(self):
        dna = copy.deepcopy(self.dna)
        dna["rules"][0]["review"] = nd.pending_review()
        with self.assertRaisesRegex(nd.Error, "per-rule"):
            nd.validate(dna, [self.work])
        del dna["rules"][0]["review"]
        with self.assertRaisesRegex(nd.Error, "requires a per-rule"):
            nd.validate(dna)

    def test_review_rejects_unread_sources_and_missing_evidence_scope(self):
        dna = copy.deepcopy(self.dna)
        dna["rules"][0]["review"]["checked_sources"][0]["chunk_ids"] = ["C999999"]
        with self.assertRaisesRegex(nd.Error, "unknown/unread"):
            nd.validate(dna)
        dna["rules"][0]["review"]["checked_sources"][0]["chunk_ids"] = ["C000001"]
        with self.assertRaisesRegex(nd.Error, "does not cover"):
            nd.validate(dna)

    def test_review_requires_attribution_alternatives_and_counter_search(self):
        for field in ("attribution", "alternative_explanations", "counterexample_search", "decision"):
            dna = copy.deepcopy(self.dna)
            dna["rules"][0]["review"][field] = " "
            with self.subTest(field=field), self.assertRaisesRegex(nd.Error, field):
                nd.validate(dna)

    def test_legacy_dna_stays_readable_with_explicit_boundary(self):
        dna = copy.deepcopy(self.dna)
        dna["schema_version"] = "1.0"
        for rule in dna["rules"]:
            rule.pop("review")
        self.assertEqual("legacy-unstructured", nd.validate(dna, [self.work])["rule_review"])
        mixed = nd.blend({"old": dna, "new": self.dna}, {"emotion": "new"}, "old", "mixed")
        self.assertEqual("1.0", mixed["schema_version"])
        nd.validate(mixed, [self.work])

    def test_blend_preserves_and_namespaces_review_provenance(self):
        mixed = nd.blend({"a": self.dna, "b": self.dna}, {"emotion": "b"}, "a", "mixed")
        self.assertEqual("1.1", mixed["schema_version"])
        for rule in mixed["rules"]:
            self.assertTrue(rule["review"]["checked_sources"][0]["source_id"].startswith(rule["id"].split("::")[0] + "::"))
        nd.validate(mixed, [self.work])

    def test_recipe_requires_explicit_bounded_eligible_selection(self):
        for ids in (["missing"], [], ["R-emotion", "R-emotion"], ["x"] * 6):
            with self.subTest(ids=ids), self.assertRaises(nd.Error):
                make_recipe(self.dna, "关系场景", ids, "balanced", [self.work])
        candidate = nd.assemble(self.work)
        with self.assertRaisesRegex(nd.Error, "threshold"):
            make_recipe(candidate, "场景", [candidate["rules"][0]["id"]], "balanced", [self.work])
        make_recipe(candidate, "场景", [candidate["rules"][0]["id"]], "exploratory", [self.work])

    def test_recipe_completion_and_revision_binding(self):
        recipe = make_recipe(self.dna, "关系场景", ["R-emotion"], "balanced", [self.work])
        check_recipe(recipe, self.dna, [self.work])
        recipe["status"] = "reviewed"
        with self.assertRaisesRegex(nd.Error, "original example"):
            check_recipe(recipe, self.dna, [self.work])
        recipe["original_example"] = "原创测试片段。"
        recipe["review_notes"] = "人工审查声明。"
        check_recipe(recipe, self.dna, [self.work])
        changed = copy.deepcopy(self.dna)
        changed["title"] = "改变的版本"
        with self.assertRaisesRegex(nd.Error, "different DNA"):
            check_recipe(recipe, changed, [self.work])
        recipe["steps"][0]["rule_id"] = "missing"
        with self.assertRaisesRegex(nd.Error, "exactly"):
            check_recipe(recipe, self.dna, [self.work])

    def test_evaluation_materials_cover_dimensions_without_gold_leakage(self):
        result = prepare_evaluation(self.root / "evaluation")
        self.assertEqual("not evaluated", result["agent_semantic_quality"])
        tasks = nd.load_json(self.root / "evaluation/agent-tasks.json")
        gold = nd.load_json(self.root / "evaluation/evaluator-gold.json")
        self.assertEqual(set(nd.DIMENSIONS), {c["dimension"] for c in tasks["cases"]})
        self.assertTrue(all("expected" not in c and "quotes" not in c for c in tasks["cases"]))
        for case in gold["cases"]:
            if case["phase"] == "training":
                self.assertTrue(all(e["chunk_id"] in tasks["training_chunks"] for e in case["evidence"]))
        self.assertEqual(0, len(nd.assemble(self.root / "evaluation/workspace")["sources"][0]["read_chunks"]))
        with self.assertRaises(nd.Error):
            prepare_evaluation(self.root / "evaluation")

    def test_new_cli_commands_and_prompt_memory(self):
        commands = [("locate", self.work, "--quote", "空杯"), ("status", self.work, "--quick"),
                    ("memory", self.work, "--before", "C000002"),
                    ("record-template", self.work, "--id", "C000002", "--out", self.root / "template.json"),
                    ("recipe", self.root / "demo/novel-dna.json", "--task", "关系场景", "--rule", "R-emotion", "--out", self.root / "recipe.json"),
                    ("recipe-check", self.root / "demo/writing-recipe.json", "--dna", self.root / "demo/novel-dna.json", "--workspace", self.work)]
        for command in commands:
            result = self.cli(*command)
            self.assertEqual(0, result.returncode, result.stderr)
            json.loads(result.stdout)
        result = self.cli("prompt", self.work, "--id", "C000002")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("UNTRUSTED_READING_MEMORY", result.stdout)
        self.assertIn("M000001", result.stdout)
        entry = self.root / "entry.json"
        nd.write_json(entry, self.memory_entry())
        result = self.cli("memory-record", self.work, "--entry", entry)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
