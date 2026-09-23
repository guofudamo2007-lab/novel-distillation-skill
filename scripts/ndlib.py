"""Local, deterministic helpers. No model calls, network access or telemetry."""
from __future__ import annotations

import bisect
import copy
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

VERSION = "0.1.1"
ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = ("style", "syntax", "vocabulary", "narrative", "character", "dialogue",
              "pacing", "scene", "suspense", "emotion", "theme_motif")
# Preserve v0.1.0 boundaries for manifests without a segmentation version.
HEADING_V1 = re.compile(
    r"^\s{0,3}(?:#{1,6}\s+\S.*|第[零〇一二三四五六七八九十百千万两\d]+[章节卷部回集].*"
    r"|(?:chapter|part|book)\s+(?:\d+|[ivxlcdm]+)\b.*|(?:序章|楔子|尾声|后记)(?:\s.*)?)$", re.I)
# Require a separator after a numbered heading so body phrases such as
# "第十六章节里..." do not split the source. Unmarked ambiguous titles need review.
HEADING = re.compile(
    r"^[ \t\u3000]{0,3}(?:#{1,6}\s+\S.*"
    r"|第[零〇一二三四五六七八九十百千万两\d]+[章节幕卷部回集](?:[ \t\u3000·:：—-]+\S.*|[ \t\u3000]*)"
    r"|(?:chapter|part|book)\s+(?:\d+|[ivxlcdm]+)\b.*"
    r"|(?:序[ \t\u3000]*[章幕]|楔[ \t\u3000]*子|尾[ \t\u3000]*声|后[ \t\u3000]*记)"
    r"(?:[ \t\u3000·:：—-]+\S.*|[ \t\u3000]*))$", re.I)
SEGMENTATION_VERSION = "2"
MAX_BYTES = 100 * 1024 * 1024


class Error(ValueError):
    """An actionable user-input error rather than an internal exception."""


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path: Path, encoding: str = "utf-8-sig", *, normalize: bool = True) -> str:
    if not path.is_file():
        raise Error(f"Not a file: {path}")
    if path.stat().st_size > MAX_BYTES:
        raise Error(f"File exceeds the 100 MiB safety limit: {path}")
    try:
        raw = path.read_bytes().decode(encoding)
    except (UnicodeError, LookupError) as exc:
        raise Error(f"Cannot decode {path} as {encoding}; pass --encoding explicitly.") from exc
    text = raw.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n") if normalize else raw
    if "\x00" in text or not text.strip():
        raise Error(f"Empty or binary-looking text: {path}")
    return text


def load_json(path: Path) -> Any:
    def reject(value: str) -> None:
        raise Error(f"Non-finite JSON value: {value}")
    def unique_keys(items: list[tuple]) -> dict:
        result = {}
        for key, value in items:
            if key in result:
                raise Error(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        return json.loads(read_text(path), parse_constant=reject, object_pairs_hook=unique_keys)
    except json.JSONDecodeError as exc:
        raise Error(f"Invalid JSON in {path}: {exc}") from exc


def write_text(path: Path, text: str, replace: bool = False) -> None:
    if path.is_symlink():
        raise Error(f"Refusing to write through a symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not replace:
        try:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
        except FileExistsError as exc:
            raise Error(f"Output already exists: {path}; choose a new output path.") from exc
    else:
        # Replace is only used for an explicitly requested chunk-record revision.
        import os
        import tempfile
        fd, temporary = tempfile.mkstemp(prefix=".nd-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)


def write_json(path: Path, value: Any, replace: bool = False) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", replace)


def schema_errors(value: Any, schema: dict, at: str = "$") -> list[str]:
    """Validate the deliberately small JSON Schema subset used by this project."""
    errors: list[str] = []
    kind = schema.get("type")
    matches = {"object": isinstance(value, dict), "array": isinstance(value, list),
               "string": isinstance(value, str), "integer": type(value) is int,
               "number": type(value) in (int, float), "boolean": type(value) is bool}
    if kind and not matches.get(kind, False):
        return [f"{at}: expected {kind}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{at}: expected one of {schema['enum']}")
    if isinstance(value, str):
        if len(value.strip()) < schema.get("minLength", 0):
            errors.append(f"{at}: must not be blank")
        if len(value) > schema.get("maxLength", len(value)):
            errors.append(f"{at}: too long")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{at}: invalid format")
    if type(value) in (int, float):
        if type(value) is float and not math.isfinite(value):
            errors.append(f"{at}: must be finite")
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            errors.append(f"{at}: out of range")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{at}: too few items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(x, sort_keys=True, ensure_ascii=False) for x in value]
            if len(set(encoded)) != len(encoded):
                errors.append(f"{at}: duplicate items")
        for i, item in enumerate(value):
            errors.extend(schema_errors(item, schema.get("items", {}), f"{at}[{i}]"))
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{at}.{key}: missing")
        for key, item in value.items():
            if key in props:
                errors.extend(schema_errors(item, props[key], f"{at}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{at}.{key}: unknown field")
    return errors


def check_shape(value: Any, name: str) -> None:
    errors = schema_errors(value, load_json(ROOT / "assets" / f"{name}.schema.json"))
    if errors:
        raise Error("\n".join(errors[:40]))


def metrics(text: str) -> dict:
    # These are codepoint/quote proxies, not tokenization, POS tags or semantic labels.
    sentences = [re.sub(r"\s", "", s) for s in re.split(r"[。！？!?]+|\.(?=\s|$)", text)]
    sentences = [s for s in sentences if s]
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    spans = list(re.finditer(r'“[^”]*”|「[^」]*」|『[^』]*』|"[^"\n]*"', text))
    quoted = sum(len(m.group()) - 2 for m in spans)
    nonspace = len(re.sub(r"\s", "", text))
    return {"characters": len(text), "nonspace_characters": nonspace,
            "sentence_count_proxy": len(sentences),
            "mean_sentence_chars_proxy": round(sum(map(len, sentences)) / max(len(sentences), 1), 3),
            "paragraph_count_blankline": len(paragraphs), "quoted_span_count": len(spans),
            "quoted_character_ratio_proxy": round(quoted / max(len(text), 1), 5)}


def segments(text: str, max_chars: int, context: int, *,
             version: str = SEGMENTATION_VERSION) -> tuple[list[dict], list[dict]]:
    if version not in ("1", "2"):
        raise Error(f"Unsupported segmentation version: {version!r}; use a compatible tool version.")
    heading = HEADING_V1 if version == "1" else HEADING
    if max_chars < 64 or not 0 <= context <= max_chars // 2:
        raise Error("--chunk-chars must be >=64; context must be between 0 and half the chunk size.")
    starts = [0]
    headings: dict[int, str] = {}
    offset = 0
    for line in text.splitlines(keepends=True):
        if heading.match(line.rstrip("\n")):
            headings[offset] = line.strip()
            if offset:
                starts.append(offset)
        offset += len(line)
    starts = sorted(set(starts))
    line_starts = [0] + [m.end() for m in re.finditer("\n", text)]
    chapters, chunks = [], []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        chapter = {"id": f"CH{i + 1:04d}", "title": headings.get(start, "Preamble / unheaded text"),
                   "start": start, "end": end}
        chapters.append(chapter)
        cursor = start
        while cursor < end:
            stop = min(cursor + max_chars, end)
            if stop < end:
                # Prefer a paragraph/line break, but never lose a long unbroken line.
                split = text.rfind("\n", cursor + max_chars // 2, stop)
                if split >= 0:
                    stop = split + 1
            chunks.append({"id": f"C{len(chunks) + 1:06d}", "chapter_id": chapter["id"],
                           "start": cursor, "end": stop,
                           "context_start": max(start, cursor - context),
                           "context_end": min(end, stop + context),
                           "line_start": bisect.bisect_right(line_starts, cursor),
                           "line_end": bisect.bisect_right(line_starts, stop - 1)})
            cursor = stop
    return chapters, chunks


def prepare(source: Path, out: Path, title: str, encoding: str, max_chars: int, context: int) -> dict:
    if source.suffix.lower() not in (".txt", ".md", ".markdown"):
        raise Error("Input must be TXT or Markdown; convert other formats with an appropriate tool first.")
    if out.exists() or out.is_symlink():
        raise Error(f"Workspace already exists: {out}; prepare a new version instead of overwriting evidence.")
    if title and not title.strip():
        raise Error("Title must not be blank.")
    text = read_text(source, encoding)
    chapters, chunks = segments(text, max_chars, context)
    fingerprint = digest(text)
    manifest = {"schema_version": "1.0", "segmentation_version": SEGMENTATION_VERSION,
                "title": title or source.stem,
                "source_id": f"src-{fingerprint[:16]}", "sha256": fingerprint,
                "input_name": source.name, "encoding": encoding,
                "normalization": "BOM removed; CRLF/CR -> LF; no other whitespace normalization",
                "coordinate_system": "zero-based Unicode codepoints, half-open [start,end)",
                "chunk_chars": max_chars, "context_chars": context,
                "chapters": chapters, "chunks": chunks, "metrics": metrics(text)}
    out.mkdir(parents=True)
    (out / "analyses").mkdir()
    write_text(out / ".gitignore", "*\n!.gitignore\n")
    write_text(out / "source.txt", text)
    write_json(out / "manifest.json", manifest)
    return manifest


def workspace(path: Path) -> tuple[dict, str]:
    if any((path / name).is_symlink() for name in ("manifest.json", "source.txt", "analyses")):
        raise Error("Workspace source, manifest and analyses must not be symlinks.")
    manifest = load_json(path / "manifest.json")
    # source.txt is already normalized; verify its exact persisted codepoints.
    text = read_text(path / "source.txt", "utf-8", normalize=False)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        raise Error("Unsupported workspace format.")
    if digest(text) != manifest.get("sha256"):
        raise Error("Source snapshot hash mismatch; prepare a fresh workspace for revised text.")
    try:
        chapters, chunks = segments(text, manifest["chunk_chars"], manifest["context_chars"],
                                    version=manifest.get("segmentation_version", "1"))
    except (KeyError, TypeError) as exc:
        raise Error("Malformed workspace configuration.") from exc
    if chapters != manifest.get("chapters") or chunks != manifest.get("chunks"):
        raise Error("Workspace offsets/chapters were changed; regenerate the workspace.")
    if manifest.get("source_id") != f"src-{digest(text)[:16]}" or manifest.get("metrics") != metrics(text):
        raise Error("Workspace source metadata was changed.")
    return manifest, text


def find_chunk(manifest: dict, chunk_id: str) -> dict:
    for chunk in manifest["chunks"]:
        if chunk["id"] == chunk_id:
            return chunk
    raise Error(f"Unknown chunk: {chunk_id}")


def check_span(span: dict, chunk: dict, text: str) -> None:
    if not chunk["start"] <= span["start"] < chunk["end"]:
        raise Error("Evidence must START in the chunk's core, not its overlap/context.")
    if not span["start"] < span["end"] <= chunk["context_end"]:
        raise Error("Evidence end is outside the chunk context, or the range is empty.")
    if text[span["start"]:span["end"]] != span["quote"]:
        raise Error("Evidence quote does not exactly match the normalized source offsets.")


def check_record(record: dict, manifest: dict, text: str) -> None:
    check_shape(record, "chunk-analysis")
    if record["source_sha256"] != manifest["sha256"]:
        raise Error("Chunk analysis belongs to a different source revision.")
    chunk = find_chunk(manifest, record["chunk_id"])
    for observation in record["observations"]:
        if not any(e["kind"] == "support" for e in observation["evidence"]):
            raise Error("Each observation needs at least one supporting source span.")
        for span in observation["evidence"]:
            check_span(span, chunk, text)


def record_analysis(path: Path, record: dict, replace: bool = False) -> dict:
    manifest, text = workspace(path)
    check_record(record, manifest, text)
    destination = path / "analyses" / f"{record['chunk_id']}.json"
    if destination.parent.is_symlink():
        raise Error("The analyses directory must not be a symlink.")
    write_json(destination, record, replace)
    return {"recorded": record["chunk_id"], "path": str(destination)}


def assemble(path: Path, title: str = "") -> dict:
    manifest, text = workspace(path)
    dna = {"schema_version": "1.0", "title": title or manifest["title"], "status": "draft",
           "review_notes": "", "sources": [{"id": manifest["source_id"], "title": manifest["title"],
           "sha256": manifest["sha256"], "total_characters": len(text),
           "total_chapters": len(manifest["chapters"]), "total_chunks": len(manifest["chunks"]),
           "read_chunks": [], "metrics": manifest["metrics"]}],
           "dimensions": {d: {"status": "unknown", "summary": "", "rule_ids": []} for d in DIMENSIONS},
           "rules": [], "evidence": [], "characters": [], "templates": [],
           "exclusions": [], "limitations": ["Candidate observations require cross-chapter distillation and counterexample review."]}
    evidence_map: dict[tuple, str] = {}
    for chunk in manifest["chunks"]:
        record_path = path / "analyses" / f"{chunk['id']}.json"
        if not record_path.exists():
            continue
        if record_path.is_symlink():
            raise Error("Analysis records must not be symlinks.")
        record = load_json(record_path)
        check_record(record, manifest, text)
        if record["chunk_id"] != chunk["id"]:
            raise Error("Record filename and chunk_id disagree.")
        dna["sources"][0]["read_chunks"].append(chunk["id"])
        for observation in record["observations"]:
            rule = {k: observation[k] for k in ("dimension", "observation", "mechanism", "instruction", "scope", "exceptions")}
            rule.update({"id": f"R{len(dna['rules']) + 1:04d}", "strength": "candidate", "confidence": "low",
                         "evidence_ids": [], "counterevidence_ids": []})
            for span in observation["evidence"]:
                key = (span["start"], span["end"], span["kind"])
                if key not in evidence_map:
                    evidence_id = f"E{len(dna['evidence']) + 1:04d}"
                    evidence_map[key] = evidence_id
                    dna["evidence"].append(dict(span, id=evidence_id, source_id=manifest["source_id"],
                                                chapter_id=chunk["chapter_id"], chunk_id=chunk["id"]))
                rule["counterevidence_ids" if span["kind"] == "counter" else "evidence_ids"].append(evidence_map[key])
            dna["rules"].append(rule)
            dimension = dna["dimensions"][rule["dimension"]]
            dimension["status"] = "observed"
            dimension["rule_ids"].append(rule["id"])
    if len(dna["sources"][0]["read_chunks"]) < len(manifest["chunks"]):
        dna["limitations"].append("Only a subset of chunks has recorded analysis; do not claim full-book coverage.")
    validate(dna, [path])
    return dna


def validate(dna: dict, workspaces: list[Path] | None = None) -> dict:
    check_shape(dna, "novel-dna")
    errors: list[str] = []

    def index(items: list[dict], label: str) -> dict:
        result = {item["id"]: item for item in items}
        if len(result) != len(items):
            errors.append(f"Duplicate {label} IDs")
        return result

    sources = index(dna["sources"], "source")
    rules = index(dna["rules"], "rule")
    evidence = index(dna["evidence"], "evidence")
    index(dna["characters"], "character")
    verified = {}
    for path in workspaces or []:
        manifest, text = workspace(path)
        verified.setdefault(manifest["sha256"], []).append((manifest, text))
    for source in sources.values():
        if source["total_chapters"] > source["total_chunks"] or source["metrics"]["characters"] != source["total_characters"]:
            errors.append(f"{source['id']}: inconsistent source counts")
        if any(not re.fullmatch(r"C[0-9]{6,}", cid) or not 1 <= int(cid[1:]) <= source["total_chunks"]
               for cid in source["read_chunks"]):
            errors.append(f"{source['id']}: invalid read chunk ID")
        if len(source["read_chunks"]) > source["total_chunks"]:
            errors.append(f"{source['id']}: read coverage exceeds total")
        if workspaces:
            if source["sha256"] not in verified:
                errors.append(f"Missing source workspace for {source['id']}")
                continue
            # The same text can have several chunk layouts. All evidence for a
            # DNA source must fit ONE layout, regardless of workspace order.
            attempts = []
            source_evidence = [item for item in evidence.values() if item["source_id"] == source["id"]]
            for manifest, text in verified[source["sha256"]]:
                problems = []
                if (source["total_characters"] != len(text) or source["total_chunks"] != len(manifest["chunks"])
                        or source["total_chapters"] != len(manifest["chapters"]) or source["metrics"] != manifest["metrics"]):
                    problems.append(f"{source['id']}: source metadata mismatch")
                known = {chunk["id"]: chunk for chunk in manifest["chunks"]}
                if not set(source["read_chunks"]) <= known.keys():
                    problems.append(f"{source['id']}: unknown read chunk")
                for item in source_evidence:
                    try:
                        chunk = known.get(item["chunk_id"])
                        if chunk is None:
                            raise Error(f"Unknown chunk: {item['chunk_id']}")
                        check_span(item, chunk, text)
                        if item["chapter_id"] != chunk["chapter_id"]:
                            problems.append(f"{item['id']}: wrong chapter")
                    except Error as exc:
                        problems.append(f"{item['id']}: {exc}")
                if not problems:
                    break
                attempts.append(problems)
            else:
                errors.extend(min(attempts, key=len))
    for item in evidence.values():
        source = sources.get(item["source_id"])
        if source is None:
            errors.append(f"{item['id']}: unknown source")
            continue
        if item["chunk_id"] not in source["read_chunks"]:
            errors.append(f"{item['id']}: evidence from an unread chunk")
        if not 0 <= item["start"] < item["end"] <= source["total_characters"]:
            errors.append(f"{item['id']}: invalid range")
        if len(item["quote"]) != item["end"] - item["start"]:
            errors.append(f"{item['id']}: quote/range length mismatch")
        if not re.fullmatch(r"CH[0-9]{4,}", item["chapter_id"]) or not 1 <= int(item["chapter_id"][2:]) <= source["total_chapters"]:
            errors.append(f"{item['id']}: invalid chapter ID")
    dimension_refs: list[str] = []
    for dim, profile in dna["dimensions"].items():
        if profile["status"] == "unknown" and profile["rule_ids"]:
            errors.append(f"{dim}: unknown dimension cannot contain rules")
        if profile["status"] == "distilled" and not profile["summary"].strip():
            errors.append(f"{dim}: distilled dimension needs a summary")
        for rule_id in profile["rule_ids"]:
            dimension_refs.append(rule_id)
            if rule_id not in rules or rules[rule_id]["dimension"] != dim:
                errors.append(f"{dim}: wrong/unknown rule {rule_id}")
    if set(dimension_refs) != set(rules) or len(dimension_refs) != len(rules):
        errors.append("Every rule must belong to exactly one matching dimension")
    for rule in rules.values():
        for field, kind in (("evidence_ids", "support"), ("counterevidence_ids", "counter")):
            for evidence_id in rule[field]:
                if evidence_id not in evidence or evidence[evidence_id]["kind"] != kind:
                    errors.append(f"{rule['id']}: wrong/unknown {kind} evidence {evidence_id}")
        supports = [evidence[e] for e in rule["evidence_ids"] if e in evidence and evidence[e]["source_id"] in sources]
        unique = {(sources[e["source_id"]]["sha256"], e["start"], e["end"]) for e in supports}
        chapters = {(sources[e["source_id"]]["sha256"], e["chapter_id"]) for e in supports}
        if rule["strength"] in ("recurring", "strong") and len(unique) < 2:
            errors.append(f"{rule['id']}: recurring rules need two distinct supporting spans")
        if rule["strength"] == "strong" and (len(unique) < 3 or len(chapters) < 3):
            errors.append(f"{rule['id']}: strong rules need three independent chapters and spans")
        if rule["confidence"] == "high" and rule["strength"] != "strong":
            errors.append(f"{rule['id']}: high confidence requires strong cross-chapter support")
    for item in dna["characters"] + dna["templates"]:
        if not set(item["rule_ids"]) <= set(rules):
            errors.append("Character/template refers to an unknown rule")
    if dna["status"] == "reviewed":
        if not dna["rules"] or not dna["review_notes"].strip():
            errors.append("Reviewed DNA needs rules and explicit review notes")
        if any(p["status"] == "observed" for p in dna["dimensions"].values()):
            errors.append("Reviewed DNA cannot contain undistilled observed dimensions")
    if errors:
        raise Error("\n".join(errors[:40]))
    return {"valid": True, "verification": "source-backed" if workspaces else "metadata-only",
            "semantic_correctness": "not machine-verified", "status": dna["status"],
            "rules": len(rules), "evidence": len(evidence),
            "coverage": [{"source_id": s["id"], "read": len(s["read_chunks"]),
                          "total": s["total_chunks"]} for s in sources.values()]}


def blend(inputs: dict[str, dict], mapping: dict[str, str], default: str, title: str) -> dict:
    if default not in inputs or set(mapping) - set(DIMENSIONS) or set(mapping.values()) - set(inputs):
        raise Error("Blend mappings must use known dimensions and source aliases.")
    for alias, dna in inputs.items():
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", alias):
            raise Error("Use simple lowercase source aliases, such as a or dialogue_source.")
        validate(dna)
    result = {"schema_version": "1.0", "title": title, "status": "draft", "review_notes": "",
              "sources": [], "dimensions": {}, "rules": [], "evidence": [], "characters": [],
              "templates": [], "exclusions": [], "limitations": [
              "Mixed DNA: resolve incompatible rules before use; dimension selection is not semantic fusion."]}
    selected: dict[str, set[str]] = {alias: set() for alias in inputs}
    for dimension in DIMENSIONS:
        alias = mapping.get(dimension, default)
        profile = copy.deepcopy(inputs[alias]["dimensions"][dimension])
        selected[alias].update(profile["rule_ids"])
        profile["rule_ids"] = [f"{alias}::{rid}" for rid in profile["rule_ids"]]
        result["dimensions"][dimension] = profile
    for alias, dna in inputs.items():
        if alias not in {mapping.get(d, default) for d in DIMENSIONS}:
            continue
        prefix = lambda value: f"{alias}::{value}"
        used_evidence: set[str] = set()
        for original in dna["rules"]:
            if original["id"] not in selected[alias]:
                continue
            rule = copy.deepcopy(original)
            rule["id"] = prefix(rule["id"])
            for field in ("evidence_ids", "counterevidence_ids"):
                used_evidence.update(rule[field])
                rule[field] = list(map(prefix, rule[field]))
            result["rules"].append(rule)
        for original in dna["evidence"]:
            if original["id"] in used_evidence:
                item = copy.deepcopy(original)
                item["id"], item["source_id"] = prefix(item["id"]), prefix(item["source_id"])
                result["evidence"].append(item)
        for source in dna["sources"]:
            result["sources"].append(dict(copy.deepcopy(source), id=prefix(source["id"])))
        for field in ("characters", "templates"):
            for original in dna[field]:
                if original["rule_ids"] and set(original["rule_ids"]) <= selected[alias]:
                    item = copy.deepcopy(original)
                    if "id" in item:
                        item["id"] = prefix(item["id"])
                    item["rule_ids"] = list(map(prefix, item["rule_ids"]))
                    result[field].append(item)
        result["exclusions"].extend(f"[{alias}] {x}" for x in dna["exclusions"])
        result["limitations"].extend(f"[{alias}] {x}" for x in dna["limitations"])
    validate(result)
    return result


def lexical_overlap(target: str, source: str, n: int = 16) -> dict:
    if n < 4:
        raise Error("Overlap n-gram length must be >=4.")
    target, source = re.sub(r"\s+", "", target), re.sub(r"\s+", "", source)
    grams = {target[i:i + n] for i in range(max(0, len(target) - n + 1))}
    matched = {source[i:i + n] for i in range(max(0, len(source) - n + 1)) if source[i:i + n] in grams}
    return {"n": n, "target_unique_ngrams": len(grams), "matched_unique_ngrams": len(matched),
            "matched_fraction": round(len(matched) / len(grams), 5) if grams else None,
            "interpretation": "Whitespace-stripped exact overlap only; not a style similarity, plagiarism or legal verdict."}
