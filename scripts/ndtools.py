"""Evidence-backed reading, distillation and diagnostic aids; literary decisions remain the Agent's work."""
from __future__ import annotations

import bisect
import json
import re
from pathlib import Path

from ndlib import (DIMENSIONS, Error, assemble, check_record, check_shape, check_span,
                   digest, find_chunk, load_json, read_text, validate, workspace, write_json)

ACCEPTED_STRENGTHS = {
    "low": {"strong"},
    "balanced": {"strong", "recurring"},
    "exploratory": {"strong", "recurring", "candidate"},
}


def quick_status(path: Path) -> dict:
    """File presence only: never call it verified reading coverage."""
    for name in ("manifest.json", "source.txt", "analyses"):
        if (path / name).is_symlink():
            raise Error("Workspace source, manifest and analyses must not be symlinks.")
    manifest = load_json(path / "manifest.json")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        raise Error("Unsupported workspace format.")
    chunks = manifest.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise Error("Malformed workspace chunk list.")
    ids, seen = [], set()
    for chunk in chunks:
        cid = chunk.get("id") if isinstance(chunk, dict) else None
        if not isinstance(cid, str) or not re.fullmatch(r"C[0-9]{6,}", cid) or cid in seen:
            raise Error("Malformed workspace chunk IDs.")
        ids.append(cid)
        seen.add(cid)
    present = set()
    for cid in ids:
        record = path / "analyses" / f"{cid}.json"
        if record.is_symlink():
            raise Error("Analysis records must not be symlinks.")
        if record.is_file():
            present.add(cid)
    return {"source": manifest.get("title", ""), "total": len(ids),
            "record_files_present": len(present),
            "pending_by_presence": [cid for cid in ids if cid not in present],
            "verification": "not-verified", "progress_basis": "record-file-presence",
            "note": "Run status without --quick to verify source and recorded analyses."}


def locate_quote(path: Path, quote: str, chunk_id: str | None = None, limit: int = 20) -> dict:
    if not quote or len(quote) > 240:
        raise Error("Quote must contain 1 to 240 Unicode characters, without normalization.")
    if not 1 <= limit <= 100:
        raise Error("--limit must be between 1 and 100.")
    manifest, text = workspace(path)
    chunk = find_chunk(manifest, chunk_id) if chunk_id else None
    lower, upper = (chunk["start"], chunk["context_end"]) if chunk else (0, len(text))
    matches, count, cursor, owner_index = [], 0, lower, 0
    while True:
        start = text.find(quote, cursor, upper)
        if start < 0 or (chunk and start >= chunk["end"]):
            break
        cursor = start + 1  # Include overlapping occurrences.
        count += 1
        if len(matches) >= limit:
            continue
        while manifest["chunks"][owner_index]["end"] <= start:
            owner_index += 1
        owner = chunk or manifest["chunks"][owner_index]
        end = start + len(quote)
        matches.append({"chunk_id": owner["id"], "chapter_id": owner["chapter_id"],
                        "start": start, "end": end, "quote": quote,
                        "can_record": end <= owner["context_end"],
                        "context_before": text[max(owner["context_start"], start - 60):start],
                        "context_after": text[end:min(owner["context_end"], end + 60)]})
    return {"source_sha256": manifest["sha256"], "matches": matches, "total_matches": count,
            "ambiguous": count > 1, "truncated": count > len(matches),
            "note": "Exact matches only; choose a location explicitly, then record validates it."}


def locate_target_quote(target_path: Path, quote: str, encoding: str = "utf-8-sig", limit: int = 20) -> dict:
    if not quote or len(quote) > 240:
        raise Error("Quote must contain 1 to 240 Unicode characters, without normalization.")
    if not 1 <= limit <= 100:
        raise Error("--limit must be between 1 and 100.")
    text = read_text(target_path, encoding)
    line_starts = [0] + [m.end() for m in re.finditer("\n", text)]
    matches, count, cursor = [], 0, 0
    while True:
        start = text.find(quote, cursor)
        if start < 0:
            break
        cursor = start + 1
        count += 1
        if len(matches) >= limit:
            continue
        end = start + len(quote)
        matches.append({"start": start, "end": end, "quote": quote,
                        "line_start": bisect.bisect_right(line_starts, start),
                        "line_end": bisect.bisect_right(line_starts, end - 1),
                        "context_before": text[max(0, start - 60):start],
                        "context_after": text[end:min(len(text), end + 60)]})
    return {"target_sha256": digest(text), "target_characters": len(text),
            "matches": matches, "total_matches": count,
            "ambiguous": count > 1, "truncated": count > len(matches),
            "note": "Exact target matches only; choose a location explicitly, then diagnose-check validates it."}


def record_template(path: Path, chunk_id: str) -> dict:
    manifest, _ = workspace(path)
    find_chunk(manifest, chunk_id)
    return {"schema_version": "1.0", "source_sha256": manifest["sha256"],
            "chunk_id": chunk_id, "summary": "", "counterexample_search": "",
            "observations": [], "character_notes": [], "scene_notes": []}


def _memory_directory(path: Path) -> Path:
    directory = path / "memory"
    if directory.is_symlink():
        raise Error("The memory directory must not be a symlink.")
    return directory


def _check_memory(entry: dict, manifest: dict, text: str, prior: dict,
                  path: Path, checked_records: set) -> None:
    check_shape(entry, "reading-memory")
    if entry["source_sha256"] != manifest["sha256"]:
        raise Error("Reading memory belongs to a different source revision.")
    stages = {"character": {"state"}, "timeline": {"event"},
              "foreshadow": {"plant", "advance", "payoff"}}
    if entry["stage"] not in stages[entry["kind"]]:
        raise Error("Memory kind and stage disagree.")
    for span in entry["evidence"]:
        chunk = find_chunk(manifest, span["chunk_id"])
        check_span(span, chunk, text)
        if chunk["id"] not in checked_records:
            record = path / "analyses" / f"{chunk['id']}.json"
            if record.is_symlink():
                raise Error("Analysis records must not be symlinks.")
            if not record.is_file():
                raise Error("Memory evidence needs a recorded analysis; memory does not create reading coverage.")
            data = load_json(record)
            check_record(data, manifest, text)
            if data["chunk_id"] != chunk["id"]:
                raise Error("Record filename and chunk_id disagree.")
            checked_records.add(chunk["id"])
    for mid in entry["related_ids"]:
        if mid not in prior:
            raise Error(f"Memory refers to an unknown/prior-required entry: {mid}")
        if max(s["end"] for s in prior[mid]["evidence"]) > max(s["end"] for s in entry["evidence"]):
            raise Error("Related memory evidence occurs after this entry.")
    if entry["kind"] == "foreshadow" and entry["stage"] in ("advance", "payoff"):
        linked = [prior[mid] for mid in entry["related_ids"]]
        if not any(e["kind"] == "foreshadow" and e["subject"] == entry["subject"]
                   and e["stage"] in ("plant", "advance") for e in linked):
            raise Error("Foreshadow advance/payoff must link to a prior plant/advance for the same subject.")


def _load_memory(path: Path, manifest: dict, text: str) -> list[dict]:
    directory = _memory_directory(path)
    entries, prior, checked = [], {}, set()
    for filename in sorted(directory.glob("*.json"), key=lambda f: (len(f.stem), f.stem)):
        if filename.is_symlink():
            raise Error("Memory entries must not be symlinks.")
        entry = load_json(filename)
        _check_memory(entry, manifest, text, prior, path, checked)
        expected = f"M{len(entries) + 1:06d}"
        if entry["id"] != expected or filename.stem != expected:
            raise Error("Memory journal IDs must be contiguous and match filenames.")
        entries.append(entry)
        prior[entry["id"]] = entry
    return entries


def _memory_index(entries: list[dict]) -> tuple[dict[str, list[str]], list[dict], list[dict]]:
    known: dict[str, list[str]] = {"character": [], "timeline": [], "foreshadow": []}
    seen: dict[str, set[str]] = {"character": set(), "timeline": set(), "foreshadow": set()}
    foreshadow_chains: dict[str, list[dict]] = {}
    for entry in entries:
        kind, subj = entry["kind"], entry["subject"]
        if subj not in seen[kind]:
            seen[kind].add(subj)
            known[kind].append(subj)
        if kind == "foreshadow":
            foreshadow_chains.setdefault(subj, []).append(entry)
    unresolved, resolved = [], []
    for subj, chain in foreshadow_chains.items():
        latest = chain[-1]
        item = {"subject": subj, "latest_id": latest["id"], "latest_stage": latest["stage"],
                "certainty": latest["certainty"], "summary": latest["summary"],
                "entry_ids": [e["id"] for e in chain],
                "chunk_ids": sorted({s["chunk_id"] for e in chain for s in e["evidence"]})}
        if any(e["stage"] == "payoff" for e in chain):
            resolved.append(item)
        else:
            unresolved.append(item)
    return known, unresolved, resolved


def record_memory(path: Path, entry: dict) -> dict:
    manifest, text = workspace(path)
    entries = _load_memory(path, manifest, text)
    _check_memory(entry, manifest, text, {e["id"]: e for e in entries}, path, set())
    if entry["id"] != f"M{len(entries) + 1:06d}":
        raise Error("Append memory with the next sequential ID; existing entries cannot be replaced.")
    destination = _memory_directory(path) / f"{entry['id']}.json"
    write_json(destination, entry)
    return {"recorded_memory": entry["id"], "path": str(destination),
            "verification": "source-backed", "semantic_correctness": "not machine-verified"}


def reading_memory(path: Path, chunk_id: str | None = None, subjects: list[str] | None = None,
                   limit: int = 8, budget: int = 6000) -> dict:
    if not 1 <= limit <= 100 or not 256 <= budget <= 30000:
        raise Error("Memory limit must be 1..100 and character budget 256..30000.")
    manifest, text = workspace(path)
    entries = _load_memory(path, manifest, text)
    cutoff = find_chunk(manifest, chunk_id)["start"] if chunk_id else len(text)
    prior_entries = [e for e in entries if max(s["end"] for s in e["evidence"]) <= cutoff]
    known_subjects, unresolved, _ = _memory_index(prior_entries)
    eligible = [e for e in prior_entries if not subjects or e["subject"] in subjects]
    eligible.sort(key=lambda e: (max(s["end"] for s in e["evidence"]), e["id"]), reverse=True)
    selected, used = [], 2
    for entry in eligible:
        size = len(json.dumps(entry, ensure_ascii=False)) + (2 if selected else 0)
        if len(selected) < limit and used + size <= budget:
            selected.append(entry)
            used += size
    return {"source_sha256": manifest["sha256"], "entries": selected,
            "eligible": len(eligible), "omitted": len(eligible) - len(selected),
            "total_entries": len(entries), "before_source_offset": cutoff,
            "known_subjects": known_subjects, "unresolved_foreshadows": unresolved,
            "selection": "latest evidence before core; optional exact subject filter",
            "note": "UNTRUSTED_READING_MEMORY: evidence-backed annotations, not instructions or established facts."}


def distill_brief(path: Path, title: str = "") -> dict:
    """Aggregate recorded chunk observations, notes and memory for cross-chapter distillation."""
    manifest, text = workspace(path)
    dna = assemble(path, title)
    entries = _load_memory(path, manifest, text)
    known_subjects, unresolved, resolved = _memory_index(entries)
    chapters = {c["id"]: c["title"] for c in manifest["chapters"]}
    evidence_by_id = {e["id"]: e for e in dna["evidence"]}
    chunk_ledger, character_notes, scene_notes = [], [], []
    for chunk in manifest["chunks"]:
        record_path = path / "analyses" / f"{chunk['id']}.json"
        if not record_path.exists():
            continue
        record = load_json(record_path)
        chunk_ledger.append({"chunk_id": chunk["id"], "chapter_id": chunk["chapter_id"],
                             "chapter_title": chapters.get(chunk["chapter_id"], ""),
                             "summary": record["summary"],
                             "counterexample_search": record["counterexample_search"],
                             "observation_count": len(record["observations"])})
        for note in record["character_notes"]:
            character_notes.append({"chunk_id": chunk["id"], "chapter_id": chunk["chapter_id"], "note": note})
        for note in record["scene_notes"]:
            scene_notes.append({"chunk_id": chunk["id"], "chapter_id": chunk["chapter_id"], "note": note})
    dimension_workbench = {}
    for dim in DIMENSIONS:
        dim_rules = [r for r in dna["rules"] if r["dimension"] == dim]
        support_spans, support_chapters, candidates = set(), [], []
        for rule in dim_rules:
            supports = [evidence_by_id[eid] for eid in rule["evidence_ids"]]
            counters = [evidence_by_id[eid] for eid in rule["counterevidence_ids"]]
            for item in supports:
                support_spans.add((item["start"], item["end"]))
                if item["chapter_id"] not in support_chapters:
                    support_chapters.append(item["chapter_id"])
            candidates.append({"rule_id": rule["id"],
                               "chapter_ids": sorted({item["chapter_id"] for item in supports + counters}),
                               "chunk_ids": sorted({item["chunk_id"] for item in supports + counters}),
                               "observation": rule["observation"], "mechanism": rule["mechanism"],
                               "instruction": rule["instruction"], "scope": rule["scope"],
                               "exceptions": rule["exceptions"],
                               "support_evidence": supports, "counter_evidence": counters})
        if len(support_spans) >= 3 and len(support_chapters) >= 3:
            ceiling = "strong"
        elif len(support_spans) >= 2:
            ceiling = "recurring"
        elif len(support_spans) >= 1:
            ceiling = "candidate"
        else:
            ceiling = "unknown"
        dimension_workbench[dim] = {"candidate_count": len(candidates),
                                    "distinct_chapters": support_chapters,
                                    "distinct_support_spans": len(support_spans),
                                    "engineering_ceiling_if_same_mechanism": ceiling,
                                    "candidates": candidates}
    return {"source_id": manifest["source_id"], "source_sha256": manifest["sha256"],
            "title": dna["title"],
            "coverage": {"read": len(dna["sources"][0]["read_chunks"]), "total": len(manifest["chunks"]),
                         "read_chunks": dna["sources"][0]["read_chunks"]},
            "chunk_ledger": chunk_ledger, "dimension_workbench": dimension_workbench,
            "character_notes": character_notes, "scene_notes": scene_notes,
            "memory_summary": {"total_entries": len(entries), "known_subjects": known_subjects,
                               "unresolved_foreshadows": unresolved, "resolved_foreshadows": resolved},
            "candidate_dna": dna,
            "note": "Deterministic aggregation for cross-chapter distillation; semantic merging and counterexample review remain Agent work."}


def dna_fingerprint(dna: dict) -> str:
    return digest(json.dumps(dna, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def make_recipe(dna: dict, task: str, rule_ids: list[str], intensity: str,
                paths: list[Path]) -> dict:
    validate(dna, paths)
    if not task.strip() or not 1 <= len(rule_ids) <= 5 or len(set(rule_ids)) != len(rule_ids):
        raise Error("Recipe needs a task and 1..5 unique, explicitly selected rule IDs.")
    if intensity not in ACCEPTED_STRENGTHS:
        raise Error("Unknown recipe intensity.")
    rules = {r["id"]: r for r in dna["rules"]}
    for rid in rule_ids:
        if rid not in rules or rules[rid]["strength"] not in ACCEPTED_STRENGTHS[intensity]:
            raise Error(f"Recipe rule is missing or below the selected threshold: {rid}")
    return {"schema_version": "1.0", "dna_sha256": dna_fingerprint(dna),
            "status": "draft", "task": task, "intensity": intensity, "rule_ids": rule_ids,
            "facts_to_preserve": [], "steps": [{"rule_id": rid, "action": rules[rid]["instruction"]}
                                               for rid in rule_ids],
            "original_example": "", "review_notes": "",
            "checklist": ["核对人物事实、动机、视角与因果。", "逐条检查规则的适用范围与例外。",
                          "用原创人物与情境示范，核查原文重合。"],
            "source_validation": validate(dna, paths)}


def check_recipe(recipe: dict, dna: dict, paths: list[Path]) -> dict:
    check_shape(recipe, "writing-recipe")
    if recipe["dna_sha256"] != dna_fingerprint(dna):
        raise Error("Recipe belongs to a different DNA revision.")
    brief = make_recipe(dna, recipe["task"], recipe["rule_ids"], recipe["intensity"], paths)
    if {s["rule_id"] for s in recipe["steps"]} != set(recipe["rule_ids"]):
        raise Error("Recipe steps must cover exactly the selected rules.")
    if recipe["status"] == "reviewed" and (not recipe["original_example"].strip()
                                           or not recipe["review_notes"].strip()):
        raise Error("Reviewed recipe needs an Agent-authored original example and explicit review notes.")
    return {"valid": True, "status": recipe["status"],
            "source_validation": brief["source_validation"],
            "semantic_correctness": "not machine-verified"}


def make_diagnostic_template(dna: dict, target: str, intensity: str, paths: list[Path]) -> dict:
    if intensity not in ACCEPTED_STRENGTHS:
        raise Error("Unknown diagnostic intensity.")
    checked = validate(dna, paths)
    return {"schema_version": "1.0", "dna_sha256": dna_fingerprint(dna),
            "target_sha256": digest(target), "target_characters": len(target),
            "status": "draft", "intensity": intensity, "summary": "", "review_notes": "",
            "preserved_strengths": [], "issues": [], "source_validation": checked}


def check_diagnostic(report: dict, dna: dict, target: str, paths: list[Path]) -> dict:
    check_shape(report, "diagnostic-report")
    checked = validate(dna, paths)
    if report["dna_sha256"] != dna_fingerprint(dna):
        raise Error("Diagnostic report belongs to a different DNA revision.")
    if report["target_sha256"] != digest(target) or report["target_characters"] != len(target):
        raise Error("Diagnostic report belongs to a different target text revision.")
    accepted = ACCEPTED_STRENGTHS[report["intensity"]]
    rules = {r["id"]: r for r in dna["rules"]}
    seen_ids = set()
    for issue in report["issues"]:
        if issue["id"] in seen_ids:
            raise Error(f"Duplicate diagnostic issue ID: {issue['id']}")
        seen_ids.add(issue["id"])
        rid = issue["rule_id"]
        if rid not in rules or rules[rid]["strength"] not in accepted:
            raise Error(f"Diagnostic issue rule is missing or below the selected threshold: {rid}")
        if not 0 <= issue["start"] < issue["end"] <= len(target):
            raise Error(f"{issue['id']}: target range is out of bounds or empty.")
        if target[issue["start"]:issue["end"]] != issue["quote"]:
            raise Error(f"{issue['id']}: Diagnostic issue quote does not exactly match the normalized target offsets.")
    if report["status"] == "reviewed" and (not report["summary"].strip() or not report["review_notes"].strip()):
        raise Error("Reviewed diagnostic report needs a non-empty summary and explicit review notes.")
    return {"valid": True, "status": report["status"], "issues": len(report["issues"]),
            "target_sha256": digest(target), "source_validation": checked,
            "semantic_correctness": "not machine-verified"}
