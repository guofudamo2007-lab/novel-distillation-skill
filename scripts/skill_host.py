#!/usr/bin/env python3
"""Offline installation, diagnostics and portable packages for Agent Skill hosts."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

from ndlib import Error, ROOT, VERSION

NAME = "novel-distillation-skill"
# Locations checked against the primary documentation linked in references/hosts.md.
HOSTS = {
    "grok": {"name": "Grok Build CLI", "project": ".grok/skills", "user": ".grok/skills", "cli": "grok"},
    "antigravity": {"name": "Google Antigravity IDE/app", "project": ".agents/skills",
                    "user": ".gemini/config/skills", "cli": "agy"},
    "antigravity-cli": {"name": "Google Antigravity CLI", "project": ".agents/skills",
                        "user": ".gemini/antigravity-cli/skills", "cli": "agy"},
    "codex": {"name": "Codex", "project": ".agents/skills", "user": ".agents/skills", "cli": "codex"},
    "generic": {"name": "Generic Agent / manual loading", "project": "skills", "user": None, "cli": None},
}

# Explicit public distribution resources. Never walk workspaces, .git or private files.
RESOURCES = (
    "SKILL.md", "README.md", "CHANGELOG.md", ".gitignore", "agents/openai.yaml",
    "scripts/ndlib.py", "scripts/ndtools.py", "scripts/novel_distill.py", "scripts/skill_host.py",
    "assets/chunk-analysis.schema.json", "assets/novel-dna.schema.json",
    "assets/reading-memory.schema.json", "assets/writing-recipe.schema.json",
    "assets/diagnostic-report.schema.json",
    "references/apply.md", "references/dimensions.md", "references/evaluation.md",
    "references/extraction-prompt.md", "references/output-contract.md", "references/reading-aids.md",
    "references/workflow.md", "references/hosts.md", "prompts/portable-start.md",
    "examples/run_demo.py", "examples/sample-novel.txt", "examples/run_evaluation.py",
    "examples/evaluation-novel.txt", "examples/evaluation-cases.json", "examples/run_host_demo.py",
    "tests/test_workflow.py", "tests/test_reading_aids.py", "tests/test_host_compatibility.py",
)


def profile(host: str) -> dict:
    if host not in HOSTS:
        raise Error(f"Unknown host: {host}; choose one of {', '.join(HOSTS)}.")
    return HOSTS[host]


def checked_file(root: Path, relative: str) -> Path:
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise Error(f"Distribution resources must not be symlinks: {relative}")
    if not current.is_file():
        raise Error(f"Missing distribution resource: {relative}")
    return current


def destination(host: str, project: Path | None, user: bool) -> Path:
    spec = profile(host)
    if (project is None) == (not user):
        raise Error("Choose exactly one of --project PATH or --user.")
    base = Path.home().resolve() if user else project.expanduser().resolve()
    if not base.is_dir():
        raise Error(f"Project/home directory does not exist: {base}")
    relative = spec["user"] if user else spec["project"]
    if relative is None:
        raise Error("Generic hosts have no standard user location; use --project and load SKILL.md explicitly.")
    current = base
    for part in Path(relative).parts + (NAME,):
        current = current / part
        if current.is_symlink():
            raise Error(f"Refusing to use a symlink in the install destination: {current}")
    return current


def setup_text(host: str) -> str:
    spec = profile(host)
    user_path = f"~/{spec['user']}/{NAME}/" if spec["user"] else "无统一用户目录"
    return (f"# {spec['name']} · {NAME} {VERSION}\n\n"
            f"项目目录：`{spec['project']}/{NAME}/`；用户目录：`{user_path}`。\n\n"
            "把整个包目录放到上述位置，保留 scripts/assets/references/prompts/examples。\n"
            "入口是 SKILL.md；也可把 prompts/portable-start.md 的内容发给 Agent 并指定 Skill 的实际路径。\n"
            "原生发现方式见 references/hosts.md；第三方同名 CLI 必须按其自身文档确认目录。\n\n"
            "先用可用的 Python 3.10+ 运行 scripts/skill_host.py doctor --host " + host + "。\n"
            "macOS/Linux 可用 python3，Windows 可用 py -3。路径含空格时加引号。\n"
            "确认目录已被宿主发现，再用仓库原创样例验证；目录检查和样例不能证明宿主文学分析质量。\n"
            "没有终端时按 hosts.md 降级为未校验辅助阅读，不编造 SHA/坐标/覆盖率。\n")


def payload(host: str, root: Path = ROOT) -> dict[str, bytes]:
    profile(host)
    files = {name: checked_file(root, name).read_bytes() for name in RESOURCES}
    files["HOST_SETUP.md"] = setup_text(host).encode("utf-8")
    manifest = {"skill": NAME, "version": VERSION, "host": host,
                "host_runtime_test": "not-run", "files": {
                    name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}}
    files["distribution.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return files


def install(host: str, project: Path | None, user: bool = False, root: Path = ROOT) -> dict:
    files = payload(host, root)  # Validate every source before creating a destination.
    target = destination(host, project, user)
    try:
        target.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise Error(f"Skill destination already exists: {target}; existing installs are never overwritten.") from exc
    # Exclusive writes also reject an unexpected existing file. A failed copy remains inspectable.
    for name, data in files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
    return {"installed": str(target), "host": host, "version": VERSION,
            "files": len(files), "native_discovery": "not-checked", "host_runtime_test": "not-run"}


def package(host: str, out: Path, root: Path = ROOT) -> dict:
    files = payload(host, root)
    content = io.BytesIO()
    with zipfile.ZipFile(content, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            item = zipfile.ZipInfo(f"{NAME}/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            archive.writestr(item, data)
    if out.is_symlink():
        raise Error(f"Refusing to write through a symlink: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with out.open("xb") as stream:
            stream.write(content.getvalue())
    except FileExistsError as exc:
        raise Error(f"Package already exists: {out}; choose a new output path.") from exc
    return {"package": str(out), "host": host, "version": VERSION, "files": len(files),
            "sha256": hashlib.sha256(content.getvalue()).hexdigest(), "host_runtime_test": "not-run"}


def doctor(host: str, project: Path | None = None, user: bool = False, root: Path = ROOT) -> dict:
    spec = profile(host)
    missing = []
    for relative in RESOURCES:
        try:
            checked_file(root, relative)
        except Error:
            missing.append(relative)
    target = destination(host, project, user) if project is not None or user else None
    installation = "not-inspected"
    changed = []
    if target:
        installation = "missing"
        if target.is_dir():
            installation = "present"
            for relative in RESOURCES:
                try:
                    if checked_file(target, relative).read_bytes() != checked_file(root, relative).read_bytes():
                        changed.append(relative)
                except Error:
                    changed.append(relative)
    probe = target.parent if target else None
    while probe is not None and not probe.exists():
        probe = probe.parent
    return {"host": host, "version": VERSION, "python": {"executable": sys.executable,
            "version": sys.version.split()[0], "compatible": sys.version_info >= (3, 10)},
            "missing_resources": missing, "toolchain_ready": not missing and sys.version_info >= (3, 10),
            "host_executable": shutil.which(spec["cli"]) if spec["cli"] else None,
            "install_destination": str(target) if target else None, "installation": installation,
            "different_or_missing_installed_resources": changed,
            "write_permission_hint": os.access(probe, os.W_OK) if probe else None,
            "native_discovery": "not-checked", "host_runtime_test": "not-run",
            "note": "Read-only diagnostics. No host login, model call, config change, or manuscript scan."}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("profiles", help="List documented host directory profiles")
    for command in ("install", "doctor", "pack"):
        p = sub.add_parser(command)
        p.add_argument("--host", choices=HOSTS, required=True)
        if command == "pack":
            p.add_argument("--out", type=Path, required=True)
        else:
            scope = p.add_mutually_exclusive_group(required=command == "install")
            scope.add_argument("--project", type=Path)
            scope.add_argument("--user", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "profiles":
            result = {"profiles": HOSTS, "documentation_checked": "2026-10-15", "host_runtime_test": "not-run"}
        elif args.command == "pack":
            result = package(args.host, args.out)
        elif args.command == "install":
            result = install(args.host, args.project, args.user)
        else:
            result = doctor(args.host, args.project, args.user)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if args.command == "doctor" and not result["toolchain_ready"] else 0
    except (Error, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
