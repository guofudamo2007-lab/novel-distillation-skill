# 对比、混合与应用

## 对比

```sh
python scripts/novel_distill.py compare a.json b.json --out comparison.json
```

CLI 输出 11 维并排画像、完整规则及文字完全相同的 instruction。它不计算语义距离，也不排名作品高低。由 Agent 阅读双方证据，按“相同问题的不同解法”解释差异，注明采样量是否可比；同一写法在不同视角/题材/角色中未必承担相同功能。未分析的维度不要当作没有特点。

## 按维度混合

```sh
python scripts/novel_distill.py blend --source a=a.json --source b=b.json --default a --map dialogue=b --map emotion=b --title "结构 A + 对白情绪 B" --out mixed.json
python scripts/novel_distill.py validate mixed.json --workspace workspaces/a --workspace workspaces/b
```

每个维度只选一个来源别名，其他维度来自 --default。保留来源、证据、覆盖率和原规则，不平均虚构的“文风向量”；所有 id 自动加别名前缀避免冲突。角色和模板只在其全部支撑规则被选中时保留，不留下断链。不进行模糊语义融合；结果强制 draft。

Agent 接着做冲突表：来源、冲突条件、双方规则、主规则、例外、最终改写。典型冲突是极简对白与设定解释、限知叙事与全知讽刺、持续高张力与慢节奏抒情。由目标故事需求决定优先级，而不是机械“各占 50%”。修改后的规则仍需保留证据；新增折中规则不能伪称来自原作。

## 反向诊断

```sh
python scripts/novel_distill.py diagnose novel-dna.json --target my-chapter.txt --workspace workspaces/a --out diagnostic-brief.json
```

这是**诊断准备材料**：目标代理统计、来源对照、连续字符重合检查、规则检查清单。不是自动语义审稿结果。每个真正的问题由 Agent 重新读目标段落确认。

输出诊断条目应有：目标位置/短引文；类别；实际症状；目标规则 id；适用范围；为何是问题；可能的合理解释；最小修改建议。区分三类：叙事逻辑问题、相对目标的风格偏离、个人审美取舍。不把后两类自动判成漏洞。

专门检查“旁白硬塞角色嘴里”：角色是否有说话对象和目的；是否在解释双方已知的事实；是否突然拥有作者才知道的信息；是否把本应由行动/场景表达的评价直接宣讲；说出口和内心戏是否混层。长句、复杂思想和内心戏本身都不是错误。建议可以是移回旁白、改成有动机的短回应、改为行动、删重复信息；不能只把人称换成“我”就叫修好。

## 原创改写

先记目标事实锁：人物身份/关系、发生了什么、谁知道什么、时间顺序、必须保留的台词和目标长度。仅在用户请求改写时提供改稿，默认保留原始文件并另存版本。规则是工具，不得牺牲人物动机换取“像”。

给出：最小修改版、重要修改理由、保持不变的事实、需要作者决定的分歧。再查视角、因果、角色区分、信息节奏及不必要的原文搬运。不要把来源专名、标志性桥段或句子只换同义词迁入新稿。

## 针对任务的写作配方

Agent 先理解用户场景，按说话对象、人物动机、叙述视角与信息任务选择 1..5 条适用规则。用户不需要知道规则 ID。规则过多时优先完成核心目标，其他规则保留为备选。

```sh
python scripts/novel_distill.py recipe novel-dna.json --task "写一场两人久别重逢的场景" --rule R-emotion --rule R-dialogue --workspace workspaces/novel-v1 --out recipe-draft.json
```

CLI 只准备 draft：任务、显式规则、初步步骤、检查清单和生成时的校验快照；original_example 与 review_notes 留空。balanced/low/exploratory 使用与 export 相同的门槛，未知或重复 ID、超过五条规则、未达门槛会失败。exploratory 保留候选身份，不能借写作配方升级其证据强度。

Agent 接着填写：

- facts_to_preserve：目标人物、关系、事实、视角、时序与必须保留的信息；缺少关键事实时说明采用的假设。
- steps：把所选规则改成针对本任务的动作，每步关联有效 rule_id，并覆盖所有选定规则。
- original_example：用原创人物与情境示范，考虑适用条件。
- checklist：按任务补充可观察的检查点。
- review_notes：说明逐条适用性、例外、事实/动机检查和仍有的分歧。

填写后另存 recipe-reviewed.json，设 status=reviewed，再执行：

```sh
python scripts/novel_distill.py recipe-check recipe-reviewed.json --dna novel-dna.json --workspace workspaces/novel-v1
```

配方以 canonical JSON 的 SHA-256 绑定整份 DNA。规则变更后旧配方不能悄悄沿用。recipe-check 重新验证 DNA 与来源，不信任配方里的 source_validation 快照；检查关联、字段和完成声明，不自动判断原创性、示例质量或事实一致性。如需重合材料，可把示例另存为目标文本后执行 diagnose；其结果仍需人工解释。

`examples/run_demo.py` 提供两条规则、原创修车场景和人工填写的 reviewed 配方，用于可复现流程验证。实际文学判断评测见 [evaluation](evaluation.md)。

## 重合检查的含义

默认比较移除空白后连续 16 个 Unicode 字符的完全相同 n-gram；分母是目标文本的不同 n-gram 数。目标短于 n 时 matched_fraction 为 null，不是“零风险”。保留大小写和标点，改标点就可能避开命中；语义复制和改写式模仿也可能漏检。命中可能来自常见套话，因此它既不是风格相似度、抄袭概率，也不是合规证明。
