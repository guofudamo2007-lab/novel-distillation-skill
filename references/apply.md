# 对比、混合、临床诊断与原创应用 · v0.4.0

## 1. 多小说并排对比（Compare）

```sh
python scripts/novel_distill.py compare a.json b.json --out comparison.json
```

CLI 输出 11 维并排画像、完整规则及文字完全相同的 `instruction`。它不计算虚构的“文风距离”，也不排名作品高低。

**Agent 深度对比方法论**：
- 按**“同一叙事难题的不同机制解法”**组织对比（例如：同样处理“高危环境下的信任建立”，A 书靠连续技术动作配合与器物交接，B 书靠高压审讯式短促问答与信息截留）。
- 检查双方采样覆盖率（`read_chunks / total_chunks`）与题材/视角差异是否可比；同一句法或对白策略在第一人称限知与第三人称群像中承担的功能可能截然不同。
- 未蒸馏（`unknown`）的维度如实注明“未分析”，不得当作“该作品在此维度毫无特点”。

---

## 2. 按维度混合与冲突消解（Blend）

```sh
python scripts/novel_distill.py blend --source a=a.json --source b=b.json --default a --map dialogue=b --map emotion=b --title "结构 A + 对白情绪 B" --out mixed.json
python scripts/novel_distill.py validate mixed.json --workspace workspaces/a --workspace workspaces/b
```

每个维度只选一个来源别名，其余维度来自 `--default`。完整保留来源快照哈希、证据、覆盖率、逐条审查来源与原规则，所有 ID 自动添加 `alias::` 命名空间前缀。角色与模板仅在其全部支撑规则被选中时保留，防止断链。混合产物初始强制为 `status="draft"`。

**Agent 跨源冲突消解流程**：
维度选源不等于语义自洽。Agent 必须审查以下高频跨源冲突，并在 `review_notes`、规则 `scope`/`exceptions` 及 `exclusions` 中写明裁决方案：
1. **对白密度 vs 信息投放冲突**：若来源 A 的 `narrative` 依赖长篇内省铺垫，而来源 B 的 `dialogue` 要求极简错位短句，需明确“世界观与局势信息由叙述者感官观察承担，角色对白只处理关系博弈，不替旁白做背景解释”。
2. **视角限知 vs 悬念埋设冲突**：若来源 A 为严格单人贴身限知，而来源 B 的 `suspense` 含多视角信息差，需将悬念规则收敛为“仅通过当前视角人物可感知的物理反常与他人的矛盾证词建立信息差”。
3. **节奏张力 vs 情绪留白冲突**：明确高冲突推进段与低冲突缓冲段的切换边界（用 `scope` 隔离，而非机械各占 50%）。
4. 修改规则以适配混合体系时，必须保留原有支撑证据并完成逐条 `review`；若新增纯折中过渡说明，放入 `review_notes` 或 `limitations`，绝不伪造原作证据坐标。

---

## 3. 结构化反向诊断闭环（Diagnose & Diagnose-Check）

将目标章节与参考 Novel DNA 对照，找出叙事病灶与机制偏离，并通过确定性工具核验每一处诊断引文。

```sh
# 第一步：生成诊断准备材料（含目标文本哈希、统计对照、重合检查与报告模板）
python scripts/novel_distill.py diagnose novel-dna.json --target my-chapter.txt --workspace workspaces/a --out diagnostic-brief.json

# 第二步：在目标章节中精确定位问题句段的全局偏移坐标 [start, end)
python scripts/novel_distill.py locate --target my-chapter.txt --quote "问题原句"

# 第三步：Agent 完成临床审稿后，保存符合 diagnostic-report.schema.json 的报告并校验
python scripts/novel_distill.py diagnose-check diagnostic-report.json --dna novel-dna.json --target my-chapter.txt --workspace workspaces/a
```

### 四大临床诊断分类（`issues[].category`）

Agent 必须通读目标章节全文，将发现的问题严格归入以下四类（不把个人审美偏好误判为逻辑漏洞）：

1. **`logic_defect`（叙事逻辑与视角/因果漏洞）**：
   - **视角越界（POV Breach）**：限知视角人物突然在内心独白中知道其感官或既有经历不可能获知的秘密、他人心理或全知设定。
   - **人物失忆或动机断裂**：人物行为与前文已确立的事实锁、性格底线或当下处境严重冲突且无合理铺垫。
   - **信息早泄（Premature Disclosure）**：悬念尚未铺垫完成，便由旁白或角色直接把底牌说穿。
2. **`mouthpiece_warning`（角色传声筒综合征）**：
   - 角色脱离说话对象与当下动机，替作者向读者宣讲世界观设定（“正如我们大家都知道的……”）；
   - 角色用总结性、书面化的心理分析直接翻译自己的潜台词或归纳本章中心思想；
   - 原本应由动作、器物状态或场景碰撞自然呈现的关系变化，被塞进角色嘴里直白念出；
   - 说出口的台词与未说出口的内心戏混层。
3. **`style_divergence`（相对目标 DNA 的风格与机制偏离）**：
   - 在符合目标规则 `scope` 的场景中，违反了所选 DNA 规则或触发了 `exclusions` 禁区（例如：在已用器物动作传达情绪后，紧接着用冗余的抽象情绪形容词重复解释；或在需要克制留白处出现典型 **AI 腔套话**——“不仅…更…”、“某种意义上”、“空气仿佛凝固了”、“眼神里闪过一丝不易察觉的…”）。
   - **机制滥用（Scope Mismatch）**：在规则明确标注为 `exceptions` 的场景（如紧急逃生、下达抢险命令）中，仍生搬硬套“低冲突含蓄借物回避”规则，导致人物反应失真。
4. **`aesthetic_choice`（有合理动机的审美取舍）**：
   - 虽然与参考 DNA 某条规则不同，但在目标章节的特定人物性格或戏剧任务下具备充分合理性；提供对照说明与可选微调，不强制改稿。

### 诊断报告编写要求（`assets/diagnostic-report.schema.json`）

- **`preserved_strengths`**：先列出目标章节中已经成立、改写时不得破坏的亮点与核心事实（防止审稿变成推倒重写）。
- **`issues`**：按 `D0001`、`D0002` 连续编号；每条必须绑定有效的 `rule_id`、通过 `locate --target` 核实的准确 `[start, end)` 与 `quote`（1..240 字符）、具体症状 `symptom`、为何构成问题 `why_problematic`、可能的替代合理解释 `alternative_interpretation`，以及最小可操作修复方案 `minimal_fix`（例如：移回旁白、改为带当下动机的短回应、用具体动作替换情绪标签、删去段尾总结升华）。
- 设为 `status="reviewed"` 时，`summary` 与 `review_notes` 必须非空，再运行 `diagnose-check` 验证目标哈希、DNA 版本绑定与全部引文坐标。

---

## 4. 原创改写与去 AI 腔铁律（Rewrite）

仅在用户明确要求改写时执行，默认保留原始文件并另存新版本：

1. **先立事实锁（Fact Lock）**：锁定人物身份与称谓、当前关系阶段、已发生事件、各方知情边界（谁知道什么、谁不知道什么）、时间顺序及必须保留的关键台词。**规则服务于人物与故事，绝不牺牲人物动机去迎合某种“文风标签”。**
2. **只迁机制，不搬内容**：严禁将参考小说的专名、标志性器物（如把原作的“蓝铅笔/空茶杯”原封不动塞进无关题材）或原句同义词替换后迁入新稿。应根据新故事的场景物理环境，选择属于新人物职业与处境的本土器物和动作。
3. **清理伪风格化与 AI 腔**：
   - 删除动作完成后的解释性尾巴（如写完“他把扳手放回空凳旁”，删去“无声地诉说着他内心的挽留”）；
   - 将抽象情绪词（“心中五味杂陈”、“感到一阵莫名的焦躁”）拆解为具体的感官阻滞或手部操作偏差；
   - 让对白紧扣说话者对听话者的即时企图（试探、施压、敷衍、安抚），拒绝无对象的抒情独白。
4. **改后复核**：对照事实锁、角色区分度、信息释放节奏与 `diagnose` 的连续字符重合检查，向用户清晰交代改了哪里、为何这样改、保留了哪些事实及仍需作者拍板的分歧。

---

## 5. 针对任务的写作配方（Recipe & Recipe-Check）

当用户需要针对某个具体原创场景（如“写一场师徒决裂前夜的试探”）应用 DNA 时，Agent 按场景目标、人物关系与视角从 DNA 中挑选 **1..5 条** 最契合的规则：

```sh
python scripts/novel_distill.py recipe novel-dna.json --task "写一场两人久别重逢的场景" --rule R-emotion --rule R-dialogue --workspace workspaces/novel-v1 --out recipe-draft.json
```

CLI 生成绑定 `dna_sha256` 的草稿后，Agent 负责补全：
- `facts_to_preserve`：本场景的人物、关系、前置事实、知情边界与时序假设；
- `steps`：将所选规则转化为本场景的具体执行步骤（覆盖全部所选 `rule_ids`）；
- `original_example`：使用全新人物与场景撰写的原创示范片段（严格遵守适用范围与禁区）；
- `checklist` 与 `review_notes`：逐条说明规则适用性、例外规避与自检点。

完成后将 `status` 设为 `"reviewed"` 并另存，执行确定性校验：

```sh
python scripts/novel_distill.py recipe-check recipe-reviewed.json --dna novel-dna.json --workspace workspaces/novel-v1
```

---

## 6. 连续字符重合检查（Lexical Overlap）的真实边界

`diagnose` 默认比较移除空白后连续 16 个 Unicode 字符的完全相同 n-gram，分母为目标文本的唯一 n-gram 数（目标短于 `n` 时 `matched_fraction` 为 `null`，代表样本过短无法计算，而非“零风险”）。
该指标仅用于预警意外搬运的连续原句片段；改换标点或同义词即可避开命中，常见公文或套话也可能产生命中。因此它**既不是风格相似度评分，也不是抄袭率或法律合规证明**。
