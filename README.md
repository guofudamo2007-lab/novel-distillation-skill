# Novel Distillation Skill

> 将一部长篇小说“蒸馏”为可分析、可复用、可执行的写作系统。

**v0.3.0 · Grok Build / Antigravity / Codex / 通用 Agent Skill + Python 本地工具链**

不是剧情摘要器，不是模型权重蒸馏，也不是换词仿写器。它让 Agent 从用户提供的原文中抽取证据，再把文笔、文风、叙事、人物与结构提炼为 **Novel DNA**，用于研究、原创写作指导、章节诊断与机制迁移。

```text
用户提供小说 TXT / Markdown
        ↓
Prepare：归一化快照 · 标题/章节切分 · 有界上下文 · 版本哈希
        ↓
Extract：Agent 逐片阅读，记录观察、短证据与反例
        ↓
Distill：跨章合并机制，区分候选/重复/强特征，复核适用范围
        ↓
Validate：结构 · 引用 · 覆盖率 · 原文逐字核对
        ↓
Quick Profile / Deep Analysis / Novel DNA / Style Bible / Writing Constraints
        ↓
对比 · 按维度混合 · 章节诊断 · 原创改写辅助
```

## 实现范围

| 能力 | 当前实现 |
|---|---|
| 可安装 Skill | 根目录 SKILL.md、渐进式参考文档、agents/openai.yaml |
| 宿主适配 | Grok Build CLI、Antigravity IDE/app/CLI、Codex 的目录配置；通用路径入口、离线安装/诊断/打包 |
| 跨模型交接 | 显式导入单层 JSON 代码围栏、引文文件避免 shell 转义、沿用同一工作区续读；原校验不变 |
| 原文处理 | TXT/Markdown，显式编码，支持幕/带空格的序尾声/分隔标题，切分版本兼容旧工作区 |
| 长篇与续读 | core 无重叠、context 仅辅助理解、每片记录、pending 队列、版本校验 |
| 11 维蒸馏 | 文风、句法、词汇、叙事、人物、对白、节奏、场景、悬念、情绪、主题母题 |
| 结构化产物 | 四套 JSON Schema、角色语言指纹、场景/章节模板、风格禁区；DNA 1.1 兼容旧 1.0 |
| 跨章阅读记忆 | 带证据的人物状态、时间线与伏笔阶段；追加记录、推测区分、提示前文有界检索 |
| 逐条规则审查 | 实际检查片段、反例搜索、角色/叙述归属、替代解释与决定；新版升格前要求审查 |
| 阅读辅助 | 精确引用定位、重复句候选、待填记录模板、明确未验证的轻量进度 |
| 写作配方 | 为具体任务选择 1..5 条规则，Agent 补事实锁、步骤、原创示例与检查清单 |
| 证据与反例 | 原文位置、短引用逐字校验、来源版本、规则引用、强特征最低支持门槛 |
| 五类导出 | Quick Profile、Deep Analysis、Novel DNA、Style Bible、Writing Constraints；Markdown 均保留审查与覆盖边界 |
| 多小说应用 | 11 维并排对比、维度选源混合、ID 自动隔离、来源保留 |
| 诊断辅助 | 目标统计、规则检查清单、连续字符重合预警；语义判断由 Agent 完成 |
| 质量保证 | 标准库 unittest、原创可复现实例、15 项人工评测材料与保留章节、GitHub Actions 配置 |

**职责边界：** Python 命令不调用任何模型、不联网、不需要 API 密钥。它不会凭关键词自动识别人物情绪、伏笔或“文风相似度”。阅读、解释、蒸馏、冲突处理与改写由运行 Skill 的 Agent 完成。宿主模型本身仍可能接收原文内容，不应把整个工作流描述为完全离线。

## 安装与调用

需要 Python **3.10+**，无需 `pip install`。`python` 不可用时使用系统对应的 `python3` 或 Windows `py -3`。

### Grok CLI、Google Antigravity 和其他 Agent

下载完整仓库后，在仓库根目录执行（项目路径需已存在；Windows 可将 `python3` 换成 `py -3`）：

```sh
python3 scripts/skill_host.py install --host grok --project "/path/to/project"
python3 scripts/skill_host.py install --host antigravity --project "/path/to/project"
python3 scripts/skill_host.py doctor --host grok --project "/path/to/project"
```

Grok Build 安装到 `.grok/skills/novel-distillation-skill/`；Antigravity 安装到 `.agents/skills/novel-distillation-skill/`。Antigravity CLI 可选择 `--host antigravity-cli`，Codex 可选择 `--host codex`；`--user` 可替代 `--project` 安装到各自用户目录。已有目录会拒绝覆盖。

目录依据 [Grok 官方文档](https://docs.x.ai/build/features/skills-plugins-marketplaces) 和 [Antigravity 官方文档](https://www.antigravity.google/docs/skills?tab=ide) 核对；同名第三方 Grok CLI 按自己的发现机制使用。安装后在宿主里确认技能可见，或明确要求读取 Skill 实际路径下的 SKILL.md，使用 [通用启动提示词](prompts/portable-start.md)，无需 `$skill` 专有语法。

```sh
# 给其他机器分发完整、带文件哈希清单的 ZIP；不包含用户小说或分析工作区
python3 scripts/skill_host.py pack --host grok --out outputs/grok-v030.zip
python3 scripts/skill_host.py pack --host antigravity --out outputs/antigravity-v030.zip

# 只验证目录、打包与安装后工具链；不调用 Grok/Antigravity 模型
python3 examples/run_host_demo.py --out outputs/host-check
```

当前提供官方目录适配和本地工具链验证，不宣称已在这些宿主登录并完成模型端到端认证。没有终端或写入能力时，可对可见原文做明确未校验的辅助分析，或让用户本地运行命令交接记录；不要生成虚假的 SHA、坐标或已读覆盖。完整的目录表、操作系统用法、诊断边界和续读流程见 [宿主适配指南](references/hosts.md)。

### 安装到 Codex 当前项目

在准备使用 Skill 的项目根目录执行：

```sh
git clone https://github.com/guofudamo2007-lab/novel-distillation-skill.git .agents/skills/novel-distillation-skill
```

也可将整个 Skill 目录放到用户级 `~/.agents/skills/novel-distillation-skill`。不要只复制 SKILL.md：scripts、assets、references 都需要保留。安装路径与发现方式参见 [Codex 官方 Skill 文档](https://developers.openai.com/codex/skills/)；格式参见 [Agent Skills 规范](https://agentskills.io/specification)。其他支持 Agent Skills 的宿主按其安装方式使用，尚未逐个宿主做运行认证。

然后直接对 Agent 说：

```text
使用 $novel-distillation-skill。
对当前项目 data/小说.txt 做 Deep 蒸馏，工作目录 workspaces/小说-v1。
提炼文风、结构、角色语言和情绪机制，不要只概括剧情。
保留证据、反例和已读覆盖率。完成语义归纳后进行 source-backed 校验，
输出 Novel DNA、Style Bible 和 balanced 写作约束。
不要修改原文，不要把原文或分析工作目录上传到仓库。
```

任务路径以你实际文件为准。只有书名没有原文时，Skill 不会冒充已经读过该书。

## 先运行原创样例

下面命令从本仓库根目录执行。样例使用仓库自写的三章短篇和**明确人工标注**的观察，不调用 LLM，也不假装在测试模型文学能力。

```sh
python examples/run_demo.py --out outputs/demo
python scripts/novel_distill.py validate outputs/demo/novel-dna.json --workspace outputs/demo/workspace
python -m unittest discover -s tests -v
```

样例生成六处证据、两条跨章规则，只有 emotion/dialogue 两维被蒸馏，其余九维如实保留 unknown。`outputs/demo/exports/` 中有五类交付文件。重复执行时换一个输出目录，避免覆盖。

样例另外保存逐条规则审查、一条带证据的阅读记忆和人工完成的原创修车场景写作配方。可验证配方或准备独立的文学判断评测材料：

```sh
python scripts/novel_distill.py recipe-check outputs/demo/writing-recipe.json --dna outputs/demo/novel-dna.json --workspace outputs/demo/workspace
python examples/run_evaluation.py --out outputs/evaluation-session
```

评测材料覆盖 11 个维度、同一角色面对不同对象、人物证词冲突、伏笔与第四章反例。先冻结前三章 DNA，再开放第四章；Agent 不提前读 evaluator-gold.json。准备材料的命令仅核对人工证据位置，不测试模型文学能力。详见 [评测流程](references/evaluation.md)。

### v0.2.0 阅读辅助

```sh
# Agent 先生成待填模板、阅读，再定位短引文；模板不是分析结果
python scripts/novel_distill.py record-template workspaces/novel-v1 --id C000001 --out chunk-result.json
python scripts/novel_distill.py locate workspaces/novel-v1 --id C000001 --quote "准确的短原句"

# 片段 record 后才能追加带证据的阅读记忆
python scripts/novel_distill.py memory-record workspaces/novel-v1 --entry memory-entry.json
python scripts/novel_distill.py prompt workspaces/novel-v1 --id C000002 --memory-subject "角色或线索名称"

# 文件存在进度，用于安排续读；报告覆盖率前仍运行完整 status
python scripts/novel_distill.py status workspaces/novel-v1 --quick

# Agent 按任务选择规则并完成草稿，recipe 不自动生成文学示例
python scripts/novel_distill.py recipe outputs/demo/novel-dna.json --task "两人久别重逢" --rule R-emotion --rule R-dialogue --workspace outputs/demo/workspace --out outputs/recipe-draft.json
```

跨章记忆有字符预算、条数限制和 omitted 提示；按 subject 补查遗漏的关键人物或线索。新版 DNA 每条规则包含 review，recurring/strong 和整体 reviewed 需要逐条审查声明。旧工作区与旧 DNA 保持可读，旧 DNA 明确标记 legacy-unstructured，不自动宣称符合新审查。详见 [阅读辅助](references/reading-aids.md)、[数据契约](references/output-contract.md) 和 [配方流程](references/apply.md)。

## 完整命令流程

```sh
# 1. 只做原文准备，不声称完成分析
python scripts/novel_distill.py prepare data/novel.txt --out workspaces/novel-v1 --title "目标小说"

# 非 UTF-8 原文需显式指定编码；不要静默乱码继续分析
# python scripts/novel_distill.py prepare data/novel.txt --encoding gb18030 --out workspaces/novel-v1

# 2. 检查章节识别、阅读进度和待处理片段
python scripts/novel_distill.py status workspaces/novel-v1
python scripts/novel_distill.py chunk workspaces/novel-v1 --id C000001
python scripts/novel_distill.py prompt workspaces/novel-v1 --id C000001

# 3. Agent 阅读后产出符合 schema 的 chunk-result.json，再逐字校验并记录
python scripts/novel_distill.py record workspaces/novel-v1 --analysis chunk-result.json
# 修订已记录的片段时显式加 --replace；其他命令不覆盖已有输出

# 4. 组装候选记录；这一步不是语义蒸馏
python scripts/novel_distill.py assemble workspaces/novel-v1 --out outputs/candidate-dna.json

# 5. Agent 按 SKILL.md 做跨章归纳/反例审查，另存 outputs/novel-dna.json
# 然后校验、导出
python scripts/novel_distill.py validate outputs/novel-dna.json --workspace workspaces/novel-v1
python scripts/novel_distill.py export outputs/novel-dna.json --workspace workspaces/novel-v1 --out outputs/report
```

v0.1.1 的新工作区记录切分版本，已有 v0.1.0 工作区仍按原规则校验，证据和已读记录不会自动迁移。新规则识别“第一幕 夜航”“序 章”“楔子·归途”；中文序号与标题之间需要空白或分隔符，无分隔标题与未标记卷名仍须人工检查。需更新分章时另建工作区，切勿修改旧 manifest。

Quick 抽样先保存各册、位置层、片段与选择理由，区分整章和章内窗口，明确未读范围。详见工作流。

全部子命令可通过 `--help` 查看。数据契约见 [output-contract](references/output-contract.md)，阅读策略见 [workflow](references/workflow.md)。没有 `--workspace` 的 validate 只能检查元数据与内部引用，不能验证原文真实性；带参数的校验仍不能证明文学判断正确。

### 对比、混合、诊断

```sh
python scripts/novel_distill.py compare a.json b.json --out outputs/comparison.json
python scripts/novel_distill.py blend --source a=a.json --source b=b.json --default a --map dialogue=b --map emotion=b --title "A 结构 + B 对白情绪" --out outputs/mixed.json
python scripts/novel_distill.py validate outputs/mixed.json --workspace workspaces/a --workspace workspaces/b
python scripts/novel_distill.py diagnose outputs/novel-dna.json --target data/my-chapter.txt --workspace workspaces/novel-v1 --out outputs/diagnostic-brief.json
```

混合只是按维度选源，输出强制 draft；语义冲突需 Agent 再处理。诊断命令生成审稿材料，不自动宣布“角色伪人”“这里有漏洞”。参见 [应用指南](references/apply.md)。

## 不是空泛的“文风标签”

一条有效规则应当有：

> **观察**：关系变化通过物件位置出现，而非由角色解释心理。
>
> **机制**：让读者从行动中推断未说破的关系。
>
> **执行**：在人物不愿直说的低冲突场景，用同一物件的状态变化承载情绪。
>
> **例外**：需要明确事实、紧急协调时，不应故意含糊。
>
> **依据**：来源版本、章节、片段、原文范围、支持证据与反例。

规则、人物指纹、模板之间有可校验引用。全书倾向与某个角色习惯分开；内容与风格分开；没有证据的维度保持 unknown，不为了填表制造结论。

## 局限与安全

- 当前原生输入只有 TXT/Markdown，没有 PDF/EPUB/DOCX 导入、OCR、爬虫、模型 API 适配器或自动微调。
- 标题识别可能把目录、卷名、小节识别为分段；需先检查。程序的 strong 门槛不能替代真实跨章文学审查。
- 句长与引号比例是可复核的简易代理统计，不是分词、词性、真实对白占比或情绪识别。重合检查不是风格评分、抄袭概率或合规保证。
- 小说、外来 JSON 和 DNA 都作为不可信材料读取，不执行其中指令。只处理明确指定的文件，不自动扫描私人目录。
- 不提交用户原文与私有工作产物。工作目录自带 .gitignore，仓库也忽略 data/workspaces/outputs/private；这些是防误提交措施，不是访问控制。

## 项目结构

```text
SKILL.md                  Skill 入口与实际执行流程
agents/openai.yaml        宿主显示/调用信息
scripts/ndlib.py           本地处理、证据校验、组装与混合
scripts/novel_distill.py   17 个 CLI 子命令与报告导出
scripts/ndtools.py         引用定位、阅读记忆、轻量进度与写作配方
scripts/skill_host.py      多宿主安装、只读诊断与离线分发
prompts/                  无宿主专有语法的启动提示词
assets/*.schema.json      抽取记录和 Novel DNA 格式
references/               维度、抽取提示、工作流、契约与应用指南
examples/                 原创测试短篇 + 可复现实例
tests/                    单元、回归与端到端测试
.github/workflows/ci.yml  自动测试配置
```

项目尚未设置许可证，由仓库所有者选择。贡献时只加入有权提交的代码和原创/授权测试材料。
