# 工作流与长篇处理 · v0.4.0

## 输入与版本

先确认用户实际给出的文件、版本和目标。后补章节不一定替代全本；用户明确指定最新完整稿时以它为准。记录标题、读取范围和缺失内容。只有书名时不得假装读取过全文。

脚本支持 TXT/Markdown；默认 UTF-8 / UTF-8 BOM，其他编码显式 `--encoding gb18030` 等。只移除 BOM、统一换行，不去空行、不重新分段、不删除页码，以保持位置可追溯。PDF、EPUB、DOCX 先由适当工具转换并核对，不把目录、页眉、脚注污染后的结果当净文本。本版没有这些格式的内置解析器或 OCR。

`prepare` 创建不可覆盖的工作目录，含 `source.txt`、`manifest.json`、`analyses/` 和阻止目录内容被 Git 跟踪的 `.gitignore`。归一化全文 SHA-256 是版本锚点，不是对文件作者或真实性的认证。原文变动后创建新工作目录，旧证据不得自动移植。

## 阅读计划与标题边界

新工作区的标题识别支持中文“第…章/节/幕/卷/部/回/集”、含空格的序章/序幕/尾声/后记/楔子、英文 Chapter/Part/Book 和 Markdown 标题。中文序号及单元之后须是行尾，或用空白、`·`、冒号、破折号/连字符分隔标题；如“第二幕·归航”。此边界避免把正文中的“第十六章节里写过……”直接误分为章。无分隔的“第一章归航”或未标记的书名不能可靠区分正文，需人工确认，必要时在另存副本中补 Markdown 标题。

它不是目录清洗器；目录和小节仍可能构成 segment。先检查 `manifest.chapters`，特别检查长度异常的第一段、卷册交界、序/尾声和疑似对白。不得删除广告后沿用旧坐标；广告、出版梗概、重复卷名和章首复现引句应记录为输入问题，不能充当文学证据或额外独立支持。

自 v0.1.1 起，新 manifest 含 `segmentation_version="2"`；缺少字段的旧工作区按 v1 原规则校验。要使用新分章，请重新 `prepare` 到新目录；不要手工补版本号或修改旧 manifest。

- **Quick 模式**：先保存抽样计划，列明册/卷、开中末位置层、chunk ID、选择理由和是否预览过。跨卷抽样要检查每册均被覆盖；再补对白、动作、低冲突、转折等实际存在的场景。目的性选段不能冒充随机抽样。明确哪些是完整章节，哪些只是窗口。
- **Deep 模式**：顺序读完，遇到前文伏笔先用 `memory-record` 记 `plant`/`advance`，直到读到回收证据再记 `payoff`。每完成一个 core 保存 JSON 并 `record`。`status`（或长篇中途的 `status --quick`）列出未完成 chunk ID，可跨会话续读。
- **跨章记忆与伏笔追踪**：`prompt` 与 `memory` 自动提供 `known_subjects`（已建档角色/事件/线索）与 `unresolved_foreshadows`（待回收伏笔清单）。留意 `omitted` 计数，必要时用 `--memory-subject` 补查特定角色或线索。

片段 `core` 无重叠，完整拼接严格等于归一化全文。左右 `context` 可能重叠，只用于理解。证据开头只能来自 `core`，避免重复计数。坐标是 Unicode 码点，左闭右开 `[start, end)`。

## 两轮推理：借 `distill-brief` 从分片观察升维到跨章规则

第一轮（Extract）保留局部 `observation`、短 `evidence`、`character_notes` 与 `scene_notes`；第二轮（Distill）聚合机制而非简单拼接摘要：

1. 运行 `distill-brief WORK --out distill-brief.json` 生成跨章蒸馏工作台底稿，同时获取 `assemble` 组装的候选 DNA。
2. 对照 `distill-brief` 中的 `dimension_workbench`：将跨片段属于同一种底层机制的候选规则合并为一条规则，汇总其 `evidence_ids` 与 `counterevidence_ids`，移除被合并的冗余候选规则，同步更新 `dimensions.rule_ids`、`characters.rule_ids` 和 `templates.rule_ids`。
3. 对照 `character_notes` 与 `memory_summary` 中的人物状态链，按四维语用坐标编写 `characters` 语言指纹；对照 `scene_notes` 编写去剧情化的 `templates` 场景步骤；对照 `unresolved_foreshadows` 与 `resolved_foreshadows` 核查 `suspense` 维度的伏笔闭环情况。
4. **风格必须与内容脱钩**：例如“反复出现红伞/蓝铅笔”是来源母题观察，“以同一日常器物的状态或位置变化承载人物关系进展”才是可迁移机制。原作专名可以留在研究说明，但严禁流入通用 `instruction`。

## 逐条审查与临床应用

- 将每个重要结论反向查回原文。DNA 1.1 每条规则包含 `review`：写明实际检查的 `checked_sources`（必须覆盖该规则全部正反证据所在已读片段）、`counterexample_search`、`attribution`（叙述者 vs 视角染色 vs 角色特定对象台词）、`alternative_explanations` 与 `decision`。
- 晋升 `recurring`/`strong` 及整份 DNA 设为 `reviewed` 均要求逐条 `review.status="reviewed"`。没有足够跨章证据就保留 `candidate`。
- 章节反向诊断时，先用 `diagnose` 生成准备材料与报告模板，再用 `locate --target` 精确获取目标章节问题原句的偏移坐标，区分 `logic_defect`、`mouthpiece_warning`、`style_divergence` 与 `aesthetic_choice`，填写结构化报告并通过 `diagnose-check` 校验。

## 交付与隐私

先 `validate --workspace`，再 `export`。每份 Markdown 都保留 `review_notes`、`limitations` 和依据 `read_chunks` 计算的覆盖边界。不要把用户原文、未公开稿件、工作目录或私有分析日志提交到公共仓库。
