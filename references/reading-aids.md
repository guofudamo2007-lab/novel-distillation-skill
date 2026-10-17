# 阅读与跨章蒸馏辅助 · v0.4.0

命令中的 `SKILL_ROOT`、`WORK` 和文件路径按实际项目替换。以下工具均为确定性本地计算，无模型调用；阅读记忆、跨章合并、规则审查、临床诊断与写作示范的语义内容由 Agent 编写。

## 1. 引用定位与记录模板（Source & Target Quote Location）

```sh
# 在原文工作区中定位短引文（用于 Extract 与 Memory）
python "SKILL_ROOT/scripts/novel_distill.py" locate "WORK" --id C000001 --quote "准确的短原句"

# 在待诊断的目标章节文件中定位短引文（用于 Diagnose-Check）
python "SKILL_ROOT/scripts/novel_distill.py" locate --target "my-chapter.txt" --quote "待诊断的问题原句"

# 生成绑定版本的待填分片分析模板
python "SKILL_ROOT/scripts/novel_distill.py" record-template "WORK" --id C000001 --out chunk-result.json
```

- `locate` 保留原句的标点、空白和 Unicode 码点，不做模糊匹配；引用长度 1..240。省略 `--id` 可查工作区全篇，默认返回最多 20 个位置，`--limit` 上限 100，仍报告全部命中数。重复句报告 `ambiguous=true`，不替 Agent 选位置。
- 工作区定位中，匹配起点属于 `core`，末尾可延伸至其 `context_end`；`can_record=false` 表示跨出合法证据范围，不能直接导入。
- v0.4.0 新增 `--target FILE`（与 `WORKSPACE` 二选一）：直接对目标章节文本按相同规则去 BOM、统一 LF 后计算精确 Unicode 偏移 `[start, end)`、行号范围与前后文，供编写 `diagnostic-report.json` 使用。
- 引文含引号、换行、`$` 或反引号时，用 `--quote-file quote.txt` 替代 `--quote`，避免不同 shell 转义。模型响应仅含一层外层 JSON 代码围栏时，可用 `record ... --from-chat` 显式导入。
- `record-template` 绑定 `source_sha256` 与 `chunk_id`，但 `summary` / `counterexample_search` 留空，不能直接通过 `record`，也不计入覆盖率。

## 2. 跨章阅读记忆与未回收伏笔索引（Reading Memory & Foreshadow Ledger）

先 `record` 分片分析，再把值得跨章持续跟踪的人物状态、时间线事件与伏笔保存为符合 `assets/reading-memory.schema.json` 的 JSON：

```sh
python "SKILL_ROOT/scripts/novel_distill.py" memory-record "WORK" --entry memory-entry.json
python "SKILL_ROOT/scripts/novel_distill.py" memory "WORK" --before C000003
python "SKILL_ROOT/scripts/novel_distill.py" memory "WORK" --before C000003 --subject "某人物"
python "SKILL_ROOT/scripts/novel_distill.py" prompt "WORK" --id C000003 --memory-subject "某人物"
```

| 字段 | 用法 |
|---|---|
| `schema_version` / `source_sha256` / `id` | 固定 `"1.0"`、当前快照哈希、从 `M000001` 起连续追加 |
| `kind` / `stage` | `character/state`、`timeline/event`，或 `foreshadow/plant`、`advance`、`payoff` |
| `subject` / `summary` | 稳定的角色/事件/线索名称与短说明；`subject` 按精确名称检索 |
| `certainty` | `observed` 可见事实、`reported` 人物声称、`inferred` 分析者推测 |
| `evidence` | 1..6 个短引文，含 `chunk_id`/`start`/`end`/`quote`；必须来自已记录且校验通过的片段 |
| `related_ids` | 关联先前记忆。伏笔 `advance`/`payoff` 必须关联同 `subject` 的 `plant`/`advance` |

- `memory` 与 `prompt` 除返回有界 `entries`（默认最近 8 条、6000 字符预算）外，v0.4.0 自动附带截止当前位置前的全局索引：
  - **`known_subjects`**：按 `character`、`timeline`、`foreshadow` 分类列出所有已建档的 `subject` 名称，防止长篇续读时遗忘前文命名；
  - **`unresolved_foreshadows`**：自动汇总所有已 `plant` 或 `advance`、但在当前位置前尚未出现 `payoff` 的开放伏笔链（含 `latest_id`、`latest_stage`、`summary`、`chunk_ids`）。
- 记忆保存到 `WORK/memory/Mxxxxxx.json`，只能追加，不可覆盖。新事实推翻旧 `inferred` 推测时，新增记录并关联旧 ID。保存记忆不增加已读覆盖率。

## 3. 跨章蒸馏工作台（Distillation Brief）

在完成全部或阶段性分片 `record` 后，除运行 `assemble` 生成候选 DNA 外，可生成结构化跨章蒸馏底稿：

```sh
python "SKILL_ROOT/scripts/novel_distill.py" distill-brief "WORK" --out distill-brief.json
```

`distill-brief` 不再丢弃分片中的辅助笔记，为 Agent 提供四类确定性聚合视图：
1. **`chunk_ledger`**：按序排列的已读片段清单，含所属章节标题、`summary`、`counterexample_search` 与观察计数；
2. **`dimension_workbench`**：按 11 维分组的候选观察、跨章分布（`distinct_chapters`）、独立支持证据区间数（`distinct_support_spans`）及同机制合并时的工程强度上限（`engineering_ceiling_if_same_mechanism`）；
3. **`character_notes` & `scene_notes`**：汇总所有已读片段的人物语用笔记与场景结构笔记（保留 `chunk_id` 与 `chapter_id` 溯源），直接辅助构建 `characters` 语言指纹与 `templates` 场景模板；
4. **`memory_summary`**：包含 `known_subjects`、未回收伏笔 `unresolved_foreshadows` 与已闭环伏笔 `resolved_foreshadows`。

## 4. 轻量进度（Quick Status）

```sh
python "SKILL_ROOT/scripts/novel_distill.py" status "WORK" --quick
python "SKILL_ROOT/scripts/novel_distill.py" status "WORK"
```

`--quick` 只读取 `manifest.json` 并检查分析文件是否存在，返回 `verification="not-verified"`。用它快速安排下一个待读片段；会话结束或正式交付前必须运行不带 `--quick` 的完整 `status` 和 `validate --workspace`。
