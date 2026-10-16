# 宿主适配 · v0.3.0

本 Skill 的核心是标准 SKILL.md、参考文档、JSON 契约与本地 Python 工具链。宿主负责阅读与语义判断。安装目录、工具名称和调用方式可以不同，原文版本、证据、候选状态与覆盖率标准保持一致。

## 目录与入口

以下原生目录按 2026-10-15 官方文档核对；同名第三方 Grok CLI 需按其自身文档确认，不能由名称推定兼容。

| `--host` | 宿主 | 项目目录 | 用户目录 |
|---|---|---|---|
| grok | 官方 Grok Build CLI | .grok/skills/novel-distillation-skill | ~/.grok/skills/novel-distillation-skill |
| antigravity | Google Antigravity IDE/app | .agents/skills/novel-distillation-skill | ~/.gemini/config/skills/novel-distillation-skill |
| antigravity-cli | Google Antigravity CLI | .agents/skills/novel-distillation-skill | ~/.gemini/antigravity-cli/skills/novel-distillation-skill |
| codex | Codex | .agents/skills/novel-distillation-skill | ~/.agents/skills/novel-distillation-skill |
| generic | 其他 Agent，显式路径加载 | skills/novel-distillation-skill | 不假定统一用户目录 |

Grok Build 原生支持 SKILL.md 与技能斜杠入口；安装后可用 `grok inspect --json` 检查发现结果。见 [官方技能文档](https://docs.x.ai/build/features/skills-plugins-marketplaces) 与 [CLI 参考](https://docs.x.ai/build/cli/reference)。

Antigravity 当前默认 `.agents/skills`，旧 `.agent/skills` 仍兼容。IDE/app 与 CLI 的用户目录不同；不生成即将停用的旧 workflow 适配。可在 IDE 的 Customizations 中确认技能，或按当前界面使用 `/novel-distillation-skill`。见 [官方技能文档](https://www.antigravity.google/docs/skills?tab=ide)。

Codex 保留原来的布局与可选 agents/openai.yaml；其他宿主不依赖该文件或 `$novel-distillation-skill` 语法。不自动写入项目 AGENTS.md/GEMINI.md、宿主配置、登录信息或权限规则。其他 Agent 可直接读取明确指定目录里的 SKILL.md，并按 [通用启动提示词](../prompts/portable-start.md) 执行。

## 安装、诊断与打包

先下载本仓库完整目录。在仓库根目录执行，`/path/to/project` 换成实际已存在的项目目录：

```sh
python3 scripts/skill_host.py install --host grok --project "/path/to/project"
python3 scripts/skill_host.py install --host antigravity --project "/path/to/project"
python3 scripts/skill_host.py doctor --host grok --project "/path/to/project"
python3 scripts/skill_host.py pack --host antigravity --out outputs/antigravity-v030.zip
```

Windows 可将命令开头的 `python3` 换成 `py -3`；有 Python 3.10+ 的 `python` 也可使用。Python 的绝对路径含空格时，Bash 使用引号，PowerShell 使用 `& "C:\路径\python.exe"`。所有输入/输出路径都作为独立参数，避免用 shell 拼接未转义的原文；定位复杂引文优先使用 --quote-file。

`install` 默认只写指定项目下的新 Skill 目录。显式 `--user` 替代 `--project` 可安装到表中用户目录；generic 不提供统一用户目录。目的目录已存在或含符号链接时拒绝写入，不覆盖旧安装、不注册插件、不修改宿主设置。升级请先保留旧目录，再选择空的新位置安装；安装失败可能留下可检查的部分目录，不声称完成。

`doctor` 只检查当前分发文件、Python 版本、CLI 可执行文件的位置和明确指定项目的安装内容。toolchain_ready 表示当前分发资源齐全且 Python 版本满足要求；安装差异另列。CLI 找到不证明是官方版本、已登录或能调用模型，权限提示也不保证宿主沙箱允许写入。native_discovery/host_runtime_test 始终如实标记未检查/未运行；缺少 agy 命令也不能据此判定 Antigravity IDE 没有安装。

`pack` 生成可重复的 ZIP，内含完整白名单资源、HOST_SETUP.md、通用入口与逐文件 SHA-256 清单。只打包仓库自带代码、参考、契约和原创样例；不扫描或复制小说、工作区、私有分析、配置、凭证、Git 历史或未列入白名单的文件。把 ZIP 中整个 novel-distillation-skill 目录放到表中目标路径；不能只上传 SKILL.md 并假设脚本和相对链接仍可用。ZIP 不会替宿主安装插件。

安装后先让宿主确认能读取入口并运行 --help，再在全新的私有输出目录运行 examples/run_demo.py。可用 `python3 examples/run_host_demo.py --out outputs/host-check` 在本机验证各宿主目录布局与打包后的工具链。示例不调用宿主模型，成功不能宣称已完成真实宿主端到端认证。

## 按实际能力选择流程

| 本次会话能力 | 可做的工作 | 验证边界 |
|---|---|---|
| 文件读写 + Python 3.10+ 终端 | 完整 prepare/record/memory/validate/export | 按实际命令结果报告；语义质量仍由 Agent 审查 |
| 可看文本，不能直接执行脚本；用户可本地执行 | 手动交接片段提示与 JSON 记录 | 只有本地 record 成功才计入已记录片段，validate --workspace 成功才称 source-backed |
| 只有对话、附件或只读文件 | 可见文本的辅助分析、机制候选与反例 | 明确未校验；不虚构哈希、全局坐标、保存记录或全书覆盖 |

无法完整读取长篇时分片处理，保留 pending，不因宿主不同改成凭书名或摘要蒸馏。不要为了适配而提升工具权限、开启自动批准或安装宿主/模型 SDK。

## 手动交接与换宿主续读

1. 用户在本地对明确指定的小说执行 prepare 到新工作区，然后执行 prompt WORK --id C000001，把输出交给 Agent。它含版本、core、辅助上下文和有界前文记忆；不是整本小说的阅读证明。
2. Agent 根据可见片段编写分析记录，source_sha256/chunk_id 逐字复制；引用用本地 locate 查找。不要心算坐标。无法精确定位时保留笔记，先补定位，不伪造合格记录。
3. 本地用 record WORK --analysis reply.json 导入。若模型响应恰好是一个 JSON 代码围栏，可加 --from-chat；只去掉完整的外层围栏，不接受前后解释文字，不修补非法 JSON，也不放宽证据检查。
4. 下次对话或换模型时沿用同一个 WORK，先运行完整 status 检查版本、已记录与 pending，再按 subject 补查阅读记忆。旧1.0/新1.1 DNA 的审查边界不变，不自动重建 manifest、不把聊天记忆转换成已读覆盖。
5. 最后由 Agent 跨章合并规则、做逐条审查，并在本地 validate --workspace/export。只有辅助对话时可以交付未校验的研究笔记，不把它包装成通过 schema/来源校验的最终 DNA。

## 已验证范围

自动检查覆盖目录路由、资源完整性、中文/空格路径、不同安装根目录运行、ZIP 可复现性与白名单、手动交接的严格 JSON 导入、现有全流程回归。未在此流程登录或运行 Grok/Antigravity 模型，不宣称其文学分析质量或账户功能已认证。
