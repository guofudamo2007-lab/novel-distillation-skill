# Novel Distillation Skill

> 将一部长篇小说“蒸馏”为可分析、可复用、可执行的写作系统。

**v0.1.0 · 可运行的 Agent Skill + Python 本地工具链**

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
| 原文处理 | TXT/Markdown，显式编码，中文/英文/Markdown 标题识别，超长段落安全切分 |
| 长篇与续读 | core 无重叠、context 仅辅助理解、每片记录、pending 队列、版本校验 |
| 11 维蒸馏 | 文风、句法、词汇、叙事、人物、对白、节奏、场景、悬念、情绪、主题母题 |
| 结构化产物 | 两套 JSON Schema、角色语言指纹、场景/章节模板、风格禁区 |
| 证据与反例 | 原文位置、短引用逐字校验、来源版本、规则引用、强特征最低支持门槛 |
| 五类导出 | Quick Profile、Deep Analysis、Novel DNA、Style Bible、Writing Constraints |
| 多小说应用 | 11 维并排对比、维度选源混合、ID 自动隔离、来源保留 |
| 诊断辅助 | 目标统计、规则检查清单、连续字符重合预警；语义判断由 Agent 完成 |
| 质量保证 | 标准库 unittest、原创可复现实例、GitHub Actions 配置 |

**职责边界：** Python 命令不调用任何模型、不联网、不需要 API 密钥。它不会凭关键词自动识别人物情绪、伏笔或“文风相似度”。阅读、解释、蒸馏、冲突处理与改写由运行 Skill 的 Agent 完成。宿主模型本身仍可能接收原文内容，不应把整个工作流描述为完全离线。

## 安装与调用

需要 Python **3.10+**，无需 `pip install`。`python` 不可用时使用系统对应的 `python3` 或 Windows `py -3`。

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
scripts/novel_distill.py   11 个 CLI 子命令与报告导出
assets/*.schema.json      抽取记录和 Novel DNA 格式
references/               维度、抽取提示、工作流、契约与应用指南
examples/                 原创测试短篇 + 可复现实例
tests/                    单元、回归与端到端测试
.github/workflows/ci.yml  自动测试配置
```

项目尚未设置许可证，由仓库所有者选择。贡献时只加入有权提交的代码和原创/授权测试材料。
