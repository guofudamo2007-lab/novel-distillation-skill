# 输出契约 · DNA 1.1 / 分片 1.0 / 诊断 1.0 · v0.4.0

## 数据契约与兼容

本项目包含五套严格 JSON Schema（位于 `assets/`）：
- `chunk-analysis.schema.json`：单片段抽取契约（`1.0`）；
- `novel-dna.schema.json`：最终 Novel DNA 契约（新建默认 `1.1`，只读兼容旧 `1.0`）；
- `reading-memory.schema.json`：跨章追加式阅读记忆契约（`1.0`）；
- `writing-recipe.schema.json`：任务级原创写作配方契约（`1.0`）；
- `diagnostic-report.schema.json`：v0.4.0 新增的目标章节结构化临床诊断报告契约（`1.0`）。

运行时仅使用 Python 标准库校验核心类型子集、版本条件、内部引用与原文证据坐标；不依赖第三方 `jsonschema` 包，不解析外部 `$ref`。所有字段以 Schema 为准，未知字段一律拒绝（`additionalProperties: false`），禁止私自添加 `score: 99` 等主观评分字段。标识符必须唯一，布尔值不能冒充整数，严禁 `NaN`/`Infinity`。

不同宿主共享同一套数据契约。`record --from-chat` 仅在显式启用时剥离单层完整外层 JSON 代码围栏，不接受解释性前后文，不放宽任何证据校验门槛。

## Novel DNA 字段

| 字段 | 含义 |
|---|---|
| `schema_version` / `title` | 固定版本（`"1.1"` 或旧 `"1.0"`）与本次分析/混合配置标题 |
| `status` / `review_notes` | `draft` 或 `reviewed`；后者要求分析者写明跨章核对与反例审查说明 |
| `sources` | 来源 `id`、`title`、`sha256`、字符/章/片段总数、`read_chunks` 和明确命名的表层代理统计 |
| `dimensions` | 必须包含全部 11 个键；每项含 `status`（`unknown`/`observed`/`distilled`）、`summary`、`rule_ids` |
| `rules` | 可迁移规则：`id`、`dimension`、`observation`、`mechanism`、`instruction`、`scope`、`strength`、`confidence`、`evidence_ids`、`counterevidence_ids`、`exceptions`；`1.1` 另要求 `review` |
| `evidence` | 短原文证据：`id`、`source_id`、`chapter_id`、`chunk_id`、`start`、`end`、`quote`、`kind`（`support`/`counter`） |
| `characters` | `id`、`label`、`rule_ids`、`notes`；角色四维语用指纹，不强迫所有角色统一口吻 |
| `templates` | `name`、`steps`（至少两步功能描述）、`rule_ids`；描述场景/章节结构功能而非原作事件 |
| `exclusions` / `limitations` | 机制层禁区与已知限制/未读范围；不把未知包装成不存在 |

原文坐标位于工作区的 `manifest.json`（自 v0.1.1 起新工作区锁定 `segmentation_version="2"`，旧工作区保持 `v1` 边界）。`start`/`end` 为归一化全文从 0 开始的左闭右开 Unicode 码点坐标 `[start, end)`，短引文长度 1..240 且必须与 `end - start` 严格相等。

## 支持强度与置信度门槛

- `candidate`：局部候选，至少 1 个支持证据区间。
- `recurring`：至少 2 个不同原文支持区间。
- `strong`：至少来自 3 个不同来源章节且具备 3 个不同原文支持区间。
- `confidence`：分析者判断（`low`/`medium`/`high`），`high` 仅允许与 `strong` 同时使用。`assemble` 强制从 `candidate`/`low` 起步；`distill-brief` 会计算各维度在合并同机制观察时的理论最高工程门槛（`engineering_ceiling_if_same_mechanism`）供参考，但语义合并不由脚本自动完成。

## 验证层次（Validate / Recipe-Check / Diagnose-Check）

1. **逐条规则审查（DNA 1.1 `review`）**：
   - 必需字段：`status`（`pending`/`reviewed`）、`checked_sources`、`counterexample_search`、`attribution`、`alternative_explanations`、`decision`。
   - `checked_sources` 中的 `chunk_ids` 必须属于对应 `source_id` 的已读片段（`read_chunks`），且当 `review.status="reviewed"` 时必须完整覆盖该规则引用的全部正反证据所在片段。
   - 规则晋升为 `recurring`/`strong` 或整份 DNA 设为 `reviewed` 时，要求相关规则 `review.status="reviewed"` 且四项审查说明均非空。旧版 `1.0` DNA 返回 `rule_review="legacy-unstructured"`。
2. **阅读记忆校验（`memory-record` / `memory`）**：
   - 绑定 `source_sha256`，连续 `M` 编号，逐字核对引文且要求所属 `chunk_id` 已有合格分析记录。返回结果附带 `known_subjects` 与 `unresolved_foreshadows` 索引。
3. **写作配方校验（`recipe` / `recipe-check`）**：
   - 绑定 canonical DNA JSON 的 `dna_sha256`，校验 1..5 条规则满足对应 `intensity` 门槛，`steps` 完整覆盖所选规则；`reviewed` 状态必须包含非空的 `original_example` 与 `review_notes`。
4. **结构化章节诊断校验（`diagnose` / `diagnose-check`）**：
   - `diagnose` 输出包含 `dna_sha256`、`target_sha256`、`target_characters` 及初始 `report_template`（也可通过 `--report-out` 导出独立模板文件）。
   - `diagnose-check` 依据 `assets/diagnostic-report.schema.json` 验证：
     - `dna_sha256` 与当前 DNA 完全一致，`target_sha256` 及 `target_characters` 与归一化目标章节完全一致；
     - 每条 `issues` 具备唯一 `Dxxxx` 编号、合法的 `category`（`logic_defect` / `style_divergence` / `aesthetic_choice` / `mouthpiece_warning`）、满足当前 `intensity` 门槛的 `rule_id`；
     - 每条 `issues` 的 `[start, end)` 与 `quote` 在归一化目标章节中逐字精确匹配；
     - 当 `status="reviewed"` 时，`summary` 与 `review_notes` 必须非空。
5. **元数据 vs 原文核验**：
   - 不传 `--workspace` 时返回 `verification="metadata-only"`；传入全部来源对应的 `--workspace` 时逐字核验快照哈希、切分布局、章节/片段归属与引文，返回 `verification="source-backed"`。

## 导出（Export）

`export` 在全新的输出目录生成五份交付物：`quick-profile.md`、`deep-analysis.md`、`novel-dna.json`、`style-bible.md`、`writing-constraints.md`。所有四份 Markdown 均强制携带 `review_notes`、`limitations` 与根据 `read_chunks/total_chunks` 自动计算的覆盖率声明，绝不将局部采样渲染为全书读完。
