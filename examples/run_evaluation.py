#!/usr/bin/env python3
"""Prepare original evaluation materials and verify gold quote locations, not LLM quality."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ndlib import Error, load_json, prepare, write_json
from ndtools import locate_quote


def prepare_evaluation(out: Path) -> dict:
    if out.exists():
        raise Error(f"Evaluation output already exists: {out}")
    gold = load_json(ROOT / "examples/evaluation-cases.json")
    work = out / "workspace"
    manifest = prepare(ROOT / "examples/evaluation-novel.txt", work, "蓝线（原创评测材料）",
                       "utf-8-sig", 6000, 300)
    # Keep the model-facing task separate from the evaluator's gold expectations.
    tasks, answers = [], []
    for case in gold["cases"]:
        tasks.append({k: case[k] for k in ("id", "dimension", "phase", "task")})
        refs = []
        for quote in case["quotes"]:
            match = locate_quote(work, quote)
            if match["total_matches"] != 1 or not match["matches"][0]["can_record"]:
                raise Error(f"Gold quote must have one valid source location: {case['id']}")
            refs.append(match["matches"][0])
        answers.append(dict(case, evidence=refs))
    write_json(out / "agent-tasks.json", {"source_sha256": manifest["sha256"],
        "training_chunks": ["C000001", "C000002", "C000003"], "holdout_chunks": ["C000004"],
        "cases": tasks, "note": "Do not read evaluator-gold.json before answering. Read holdout only after freezing training DNA."})
    write_json(out / "evaluator-gold.json", {"source_sha256": manifest["sha256"], "cases": answers,
        "rubric": gold["rubric"], "note": "Human-authored expectations; alternate evidence-backed interpretations can be valid."})
    return {"prepared": str(out), "cases": len(tasks), "gold_quotes": sum(len(a["evidence"]) for a in answers),
            "gold_quote_locations": "source-backed", "agent_semantic_quality": "not evaluated",
            "reading_coverage": "not started"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(prepare_evaluation(args.out))
    except (Error, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
