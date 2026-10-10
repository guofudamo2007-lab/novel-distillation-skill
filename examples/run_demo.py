#!/usr/bin/env python3
"""Reproducible, hand-curated fixture. This does NOT call or simulate an LLM."""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ndlib import Error, assemble, prepare, record_analysis, validate, workspace, write_json
from novel_distill import export
from ndtools import check_recipe, locate_quote, make_recipe, record_memory, reading_memory

QUOTES = [
    ("她没有回头。他把另一只空杯推回柜子深处。", "“还有热水吗？”\n“壶在你身后。”"),
    ("他把那只空杯移到窗边，避开了漏雨的地方。", "“她说几点回来？”隔壁的人问。\n“茶还热。”"),
    ("周闻打开柜门，把空杯放回桌子。杯柄朝着她，和从前一样。", "“旧杯子呢？”\n“没扔。”"),
]


def make_demo(out: Path) -> dict:
    if out.exists():
        raise Error(f"Demo output already exists: {out}")
    work = out / "workspace"
    manifest = prepare(ROOT / "examples" / "sample-novel.txt", work, "留杯（仓库原创测试短篇）",
                       "utf-8-sig", 6000, 300)
    _, text = workspace(work)
    for chunk, quotes in zip(manifest["chunks"], QUOTES):
        observations = []
        for dimension, quote in zip(("emotion", "dialogue"), quotes):
            start = text.index(quote, chunk["start"], chunk["context_end"])
            observations.append({"dimension": dimension,
                "observation": "物件位置承担未说出的情绪变化。" if dimension == "emotion" else "回答借具体物件回避直接谈论关系。",
                "mechanism": "让读者从可见行为推断关系，保留人物不愿说破的部分。",
                "instruction": "用同一物件的状态变化暗示关系变化。" if dimension == "emotion" else "让回避型回应落到眼前的具体事物，而非解释自己的全部心理。",
                "scope": "人物不愿直接表达关系变化的低冲突场景",
                "exceptions": ["需要明确事实或紧急协调时，不应故意含糊。"],
                "evidence": [{"start": start, "end": start + len(quote), "quote": quote, "kind": "support"}]})
        record_analysis(work, {"schema_version": "1.0", "source_sha256": manifest["sha256"],
            "chunk_id": chunk["id"], "summary": "以杯子的处理和回避型回应呈现关系变化。",
            "counterexample_search": "检查直接解释情绪的句子：此短篇片段未见，不外推到其他作品。",
            "observations": observations, "character_notes": ["回答者不主动解释关系。"],
            "scene_notes": ["同一物件在不同时间重复出现，位置改变。"]})
    dna = assemble(work)
    write_json(out / "candidate-dna.json", dna)
    # Explicit gold annotations, not a general automatic distillation algorithm.
    distilled = []
    for dimension in ("emotion", "dialogue"):
        candidates = [r for r in dna["rules"] if r["dimension"] == dimension]
        rule = copy.deepcopy(candidates[0])
        rule["id"] = "R-" + dimension
        rule["evidence_ids"] = [e for candidate in candidates for e in candidate["evidence_ids"]]
        rule["strength"], rule["confidence"] = "strong", "high"
        rule["review"] = {"status": "reviewed", "checked_sources": [
            {"source_id": manifest["source_id"], "chunk_ids": [c["id"] for c in manifest["chunks"]]}],
            "counterexample_search": "人工检查三章；未见直接解释关系的反例，不外推到其他作品。",
            "attribution": "对白规则属于周闻面对关系追问时的回应；物件规则属于叙事呈现。",
            "alternative_explanations": "杯子也可承担生活细节功能；本样例将位置改变与关系进展并置。",
            "decision": "仅在此三章样例的低冲突关系场景保留 strong；不声称作者独有或长篇泛化。"}
        distilled.append(rule)
        dna["dimensions"][dimension] = {"status": "distilled", "summary": rule["observation"], "rule_ids": [rule["id"]]}
    dna["rules"] = distilled
    dna["status"] = "reviewed"
    dna["review_notes"] = "示例作者人工标注：核对三章六处短证据；仅两维，样本很小，不声称泛化到长篇。"
    dna["characters"] = [{"id": "speaker", "label": "周闻", "rule_ids": ["R-dialogue"],
                          "notes": "在关系问题上借物件回应；这是此短篇中的局部指纹。"}]
    dna["templates"] = [{"name": "物件映射关系", "steps": ["建立日常物件", "以人物行动改变物件状态", "留出关系解释空间"],
                         "rule_ids": ["R-emotion"]}]
    dna["exclusions"] = ["不在已经足够明确的物件动作之后重复解释同一情绪。"]
    dna["limitations"] = ["人工标注的极短原创样本，只验证流程；不是 LLM 文学分析质量评测。", "其余九维未做蒸馏。"]
    checked = validate(dna, [work])
    write_json(out / "novel-dna.json", dna)
    export(dna, out / "exports", [work], "balanced")
    match = locate_quote(work, QUOTES[0][0], "C000001")["matches"][0]
    record_memory(work, {"schema_version": "1.0", "source_sha256": manifest["sha256"],
        "id": "M000001", "kind": "character", "subject": "周闻", "stage": "state",
        "certainty": "observed", "summary": "把空杯推回柜子；未明说关系原因。", "related_ids": [],
        "evidence": [{k: match[k] for k in ("chunk_id", "start", "end", "quote")}]})
    write_json(out / "memory-before-chapter2.json", reading_memory(work, "C000002"))
    recipe = make_recipe(dna, "写一场两人久别重逢、都不愿直说的原创场景", ["R-emotion", "R-dialogue"], "balanced", [work])
    recipe["facts_to_preserve"] = ["两人曾共修自行车；重逢在修车铺；此时不解释离开的原因。"]
    recipe["original_example"] = "她停在卷帘门外。他从钉板上取下第二把扳手，放到空凳旁。\n‘还修车吗？’\n‘后轮没装。’"
    recipe["review_notes"] = "仓库作者人工示范：换用原创修车情境，只使用物件行动与回避型回答两项机制。"
    recipe["status"] = "reviewed"
    check_recipe(recipe, dna, [work])
    write_json(out / "writing-recipe.json", recipe)
    return checked


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(make_demo(args.out))
    except (Error, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
