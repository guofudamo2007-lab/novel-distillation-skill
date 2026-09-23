# 输出契约 · schema_version 1.0

## 两种 JSON

`assets/chunk-analysis.schema.json` 定义单片段抽取；`assets/novel-dna.schema.json` 定义最终配置。都使用 JSON Schema 2020-12 的基本类型子集。运行时仅用标准库校验本仓库使用的关键字；不是通用 JSON Schema 引擎，不解析外部 $ref。开发测试可额外使用 jsonschema 交叉验证，但运行时不需要它。

所有字段以 schema 为准；未知字段报错，不能擅自加 `score: 99` 等自创结论。标识符唯一，引用必须存在，布尔值不能冒充整数。JSON 不允许 NaN/Infinity。

## Novel DNA 字段

| 字段 | 含义 |
|---|---|
| schema_version / title | 固定版本与本次分析/混合配置标题 |
| status / review_notes | draft 或 reviewed；后者要求分析者写明交叉核对与反例审查 |
| sources | 来源 id、title、SHA-256、字符/章/片段总数、read_chunks 和明确命名的代理统计 |
| dimensions | 必须包含全部 11 个键；每项 status、summary、rule_ids。未知维度留 unknown/空数组 |
| rules | 可迁移规则；id、dimension、observation、mechanism、instruction、scope、strength、confidence、evidence_ids、counterevidence_ids、exceptions |
| evidence | 短原文证据；id、source_id、chapter_id、chunk_id、start、end、quote、kind |
| characters | id、label、rule_ids、notes；角色语言指纹，不是强迫所有角色统一风格 |
| templates | name、steps、rule_ids；steps 至少两步，描述结构功能而非来源事件 |
| exclusions / limitations | 机制层禁区与已知限制/缺失；不把未知包装成不存在 |

来源位置信息位于 workspace 的 manifest。自工具 v0.1.1 起，manifest 新增 segmentation_version="2"；无此字段的旧工作区继续使用 v1 边界，不重编号。此字段属于工作区，不加入两套 schema_version 1.0 分析 JSON。未知切分版本被拒绝；切换规则须新建工作区，不修改旧 manifest。start/end 为归一化全文的 Unicode 字符坐标，不是片段局部位置。原文引用最多 240 个字符，范围长度必须与 quote 一致。引用少不是授权充分的证明；公开发布还需用户自行审查材料权限。

## 支持强度与置信度

`candidate`：局部候选，至少一个支持证据。`recurring`：至少两个不同原文范围。`strong`：至少三个不同来源章节和三个不同范围。相同快照的混合别名不算新的独立来源。标题识别可能包含卷、目录或小节，分析者必须确认是真实独立章节。工程门槛通过并不能证明语义上已充分。

confidence 为 low/medium/high，是分析者判断，不是校准概率。high 仅能与 strong 同时使用，仍需要反例与范围审查。assemble 强制从 candidate/low 开始，不自动“升分”。

每条规则必须恰好归属于一个匹配的维度；正证据 kind=support，反证据 kind=counter。角色、模板的 rule_ids 也必须有效。reviewed 不能保留未经整理的 observed 维度，但允许如实保留 unknown。draft 可以导出，输出会标明状态。

## 验证层次

不带 workspace：结构、枚举、引用、内部范围与强度门槛检查，结果 metadata-only。它无法确认引用是否真来自小说，不能叫“已核验原文”。

带 `--workspace`（多个来源重复参数）：检查全部来源快照哈希、原文元数据、章节/片段位置、quote 逐字一致、已读覆盖。任何来源没有匹配工作目录都会失败。同一原文可以提供不同切分参数的多个工作目录；每个 DNA 来源的元数据与全部证据必须同时匹配其中一个完整工作目录，不能逐条拼用不同切分。快照按已保存的 UTF-8 字符读取，不再归一化；更改 BOM 或换行同样会触发版本不匹配。read_chunks 表示已提交分析的声明，不是程序能证明模型读懂了内容。

人工作业最后仍需检查：证据与结论的关联、反例是否充分、人物归属、真正章节独立性、指令是否夹带专名/原句/恶意命令。验证器不证明文学正确、原创性或法律合规。

## 导出

`export` 写五个新文件：quick-profile.md、deep-analysis.md、novel-dna.json、style-bible.md、writing-constraints.md。Markdown 研究报告默认只列证据坐标，JSON 含短引文。输出目录必须不存在，避免覆写用户文件。四份 Markdown 均附 review_notes 与 limitations，并从 read_chunks/total_chunks 自动判断是否部分覆盖；即使 status=reviewed 或 limitations 为空，也不会把部分阅读标成全文完成。未填写审查或限制时显示未知，不补造分析。文件名 deep-analysis.md 不等于已执行 Deep 全文阅读。

balanced 默认只采纳 recurring/strong；low 仅 strong；exploratory 也含 candidate。脚本按强度过滤，不凭空改变句法比例。候选不足时 constraints 会明确说明暂无合格规则，而不是生成空壳后宣称完成。
