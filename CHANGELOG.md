# Changelog

## 0.1.0 — 2026-09-23

First runnable implementation of the original Extract → Distill → Apply design.

Added the installable Skill, eleven-dimension analysis guidance, progressive references, strict JSON contracts, local text preparation and resumable chunk records, source-backed quote validation, candidate assembly, five deliverable exports, dimension-level comparison and blending, and diagnostic preparation with exact character-overlap checks.

Added a hand-curated original short-story demo, unit/integration regression tests, and a GitHub Actions matrix. Semantic analysis remains the host Agent's responsibility; no API credentials or runtime third-party dependencies are introduced.

Release checks fixed same-source validation across different chunk layouts and prevented repeated normalization of immutable source snapshots. Added regression coverage for both defects, including mixed-layout evidence rejection and snapshot BOM/line-ending tampering.
