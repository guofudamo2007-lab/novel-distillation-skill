#!/usr/bin/env python3
"""Smoke-test host directory layouts and copied toolchains, without running a host model."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ndlib import Error, write_json
from skill_host import HOSTS, install, package


def run(out: Path) -> dict:
    out = out.expanduser().resolve()
    if out.exists():
        raise Error(f"Host smoke output already exists: {out}")
    out.mkdir(parents=True)
    results = []
    for host in HOSTS:
        project = out / f"{host} 中文 project"
        project.mkdir()
        installed = install(host, project)
        root = Path(installed["installed"])
        copied_doctor = subprocess.run([sys.executable, str(root / "scripts/skill_host.py"), "doctor",
                                       "--host", host, "--project", str(project)], cwd=project,
                                      capture_output=True, text=True, encoding="utf-8")
        demo = subprocess.run([sys.executable, str(root / "examples/run_demo.py"), "--out", str(project / "demo")],
                              cwd=project, capture_output=True, text=True, encoding="utf-8")
        if copied_doctor.returncode or demo.returncode:
            raise Error(f"Copied toolchain failed for {host}: {copied_doctor.stderr}\n{demo.stderr}")
        report = json.loads(copied_doctor.stdout)
        if not report["toolchain_ready"] or report["different_or_missing_installed_resources"]:
            raise Error(f"Incomplete host distribution: {host}")
        packed = package(host, out / f"{host}.zip")
        results.append({"host": host, "copied_toolchain": "passed", "package_sha256": packed["sha256"],
                        "host_runtime_test": "not-run"})
    result = {"layouts": results, "host_runtime_test": "not-run", "note": "No host binary or model was invoked."}
    write_json(out / "host-check.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.out), ensure_ascii=False, indent=2))
    except (Error, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
