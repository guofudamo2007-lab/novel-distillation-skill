# Changelog

## 0.3.0 — 2026-10-16

Added documented Grok Build CLI and Google Antigravity IDE/app/CLI directory profiles alongside Codex and a generic explicit-path entry. New offline skill_host.py installs complete public resources without overwriting existing installs, reports read-only diagnostics, and builds reproducible ZIPs with per-file hashes. Distribution resources are explicitly allowlisted; manuscripts, workspaces, private files and host configuration are not copied.

Added a portable starting prompt and capability-based full/assisted/unverified workflows, with shared-workspace resume instructions. Existing source, quote and coverage validation stays unchanged. record --from-chat accepts exactly one outer JSON Markdown fence when explicitly requested; it still rejects prose, duplicate fields, non-finite numbers and invalid evidence. locate --quote-file reads exact UTF-8 quotes without shell interpolation or whitespace repair.

Added cross-host layout and copied-runtime smoke checks, Unicode/space-path tests, reproducible-package/privacy regressions and strict handoff-import tests. CI now also covers macOS. Checks validate local package layouts and toolchains, not host login, native discovery or literary model quality. Runtime remains standard-library-only, with no model calls, SDKs or host permission/configuration changes.

## 0.2.0 — 2026-10-09

Added exact quote location with ambiguity reporting and record templates; source-backed, append-only character/timeline/foreshadow memory with bounded pre-core prompt context; and explicitly unverified file-presence progress via status --quick.

New DNA uses schema 1.1 with per-rule review declarations covering checked source chunks, counterexample search, attribution, alternative explanations and decisions. Promotion to recurring/strong and reviewed DNA requires these declarations. Legacy 1.0 DNA and old source layouts remain readable without fabricated migration; validation and reports mark the legacy review boundary. Blending preserves review source references and their namespaces.

Added task-specific draft recipes from 1..5 explicitly selected rules and validation for Agent-completed original examples, bound to the exact DNA revision. Expanded the hand-curated demo with memory and a writing recipe. Added an original four-chapter evaluation set with 15 tasks covering all 11 dimensions, holdout counterexamples and setup/payoff evidence; preparing fixtures checks quote positions, not model literary quality.

Updated Skill instructions, contracts, workflow/application references, regression tests and CI. Runtime remains Python 3.10+ and standard-library-only, with no model calls, network access or API keys. Semantic review, relevance selection and creative examples remain Agent work.

## 0.1.1 — 2026-09-23

Fixed chapter preparation for Chinese acts, spaced special headings and punctuated titles. Numbered headings now require a title separator to avoid splitting body mentions. New workspaces pin segmentation version 2; unversioned v0.1.0 workspaces retain their original boundaries and evidence coordinates. Ambiguous unseparated headings still require input review.

All four Markdown exports now preserve review notes and limitations and label partial reading independently of reviewed status. Added seven regression tests covering the reported defects and legacy workspace compatibility.

Refined sampling and interpretation guidance: save selection rationale, distinguish chapter windows from complete scenes, exclude input boilerplate/repeated excerpts from evidence, and separate character testimony or persuasion from established facts. No analysis schema changes, model calls, or third-party runtime dependencies.

## 0.1.0 — 2026-09-23

First runnable implementation of the original Extract → Distill → Apply design.

Added the installable Skill, eleven-dimension analysis guidance, progressive references, strict JSON contracts, local text preparation and resumable chunk records, source-backed quote validation, candidate assembly, five deliverable exports, dimension-level comparison and blending, and diagnostic preparation with exact character-overlap checks.

Added a hand-curated original short-story demo, unit/integration regression tests, and a GitHub Actions matrix. Semantic analysis remains the host Agent's responsibility; no API credentials or runtime third-party dependencies are introduced.

Release checks fixed same-source validation across different chunk layouts and prevented repeated normalization of immutable source snapshots. Added regression coverage for both defects, including mixed-layout evidence rejection and snapshot BOM/line-ending tampering.
