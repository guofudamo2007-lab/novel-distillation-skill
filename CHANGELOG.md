# Changelog

## 0.1.1 — 2026-09-23

Fixed chapter preparation for Chinese acts, spaced special headings and punctuated titles. Numbered headings now require a title separator to avoid splitting body mentions. New workspaces pin segmentation version 2; unversioned v0.1.0 workspaces retain their original boundaries and evidence coordinates. Ambiguous unseparated headings still require input review.

All four Markdown exports now preserve review notes and limitations and label partial reading independently of reviewed status. Added seven regression tests covering the reported defects and legacy workspace compatibility.

Refined sampling and interpretation guidance: save selection rationale, distinguish chapter windows from complete scenes, exclude input boilerplate/repeated excerpts from evidence, and separate character testimony or persuasion from established facts. No analysis schema changes, model calls, or third-party runtime dependencies.

## 0.1.0 — 2026-09-23

First runnable implementation of the original Extract → Distill → Apply design.

Added the installable Skill, eleven-dimension analysis guidance, progressive references, strict JSON contracts, local text preparation and resumable chunk records, source-backed quote validation, candidate assembly, five deliverable exports, dimension-level comparison and blending, and diagnostic preparation with exact character-overlap checks.

Added a hand-curated original short-story demo, unit/integration regression tests, and a GitHub Actions matrix. Semantic analysis remains the host Agent's responsibility; no API credentials or runtime third-party dependencies are introduced.

Release checks fixed same-source validation across different chunk layouts and prevented repeated normalization of immutable source snapshots. Added regression coverage for both defects, including mixed-layout evidence rejection and snapshot BOM/line-ending tampering.
