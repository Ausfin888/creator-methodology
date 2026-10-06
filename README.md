# Creator Methodology

从中文视频到可追溯的逐字稿与创作者方法论。适用于 YouTube 普通视频、Shorts，以及已取得的本地音频。

**版本：0.1.0-pre.2，预发布测试版。** 作者：[Ausfin888](https://github.com/Ausfin888)。采用 [MIT 许可证](LICENSE)，保留版权声明。离线检查不代表 YouTube 下载、真实语音识别或另一台电脑安装已验证。

## 你会得到什么

- 只要逐字稿：Markdown 逐字稿、时间戳、原视频链接和来源类型。
- 单条视频提炼：完整逐字稿后附可复用规则，每条规则能回溯到时间戳。
- 整频道研究：逐期笔记、方法论总纲、观点变化与冲突记录。
- 后台留证：原始字幕或音频、元数据、修正记录和检查结果。

这是供 AI Agent 使用的技能包，需要支持 Agent Skills 的工具和一次环境准备。不是上传链接即可使用的独立网站。AI 负责解释和提炼；原文、时间戳和确定性检查是证据基础。

## 支持范围

| 能力 | 当前边界 |
|---|---|
| 字幕读取与清洗 | SRT / VTT，Python 3.11+；中文优先，其他语言需人工检查 |
| 无字幕本地转录 | Apple Silicon Mac，mlx-whisper + PyAV；默认中文 |
| 视频下载 | yt-dlp；Shorts 沿用视频下载流程，受网络与平台变化影响 |
| 方法论提炼 | 由 Agent 阅读完整逐字稿；不保证一定存在可复用规则 |
| Windows / Linux 本地转录 | 本版本未适配，不能当作已支持 |
| 自动后台监控 | 不包含；按用户请求执行 |

## 安装与首次使用

1. 从 [GitHub 项目](https://github.com/Ausfin888/creator-methodology) 下载项目 ZIP 并解压，将项目文件夹保存为 `creator-methodology`，放进你的 Agent 所支持的技能目录。`SKILL.md` 应在该文件夹第一层；具体目录以你的 Agent 文档为准。
2. 准备 Python 3.11+、[uv](https://docs.astral.sh/uv/getting-started/installation/)、[yt-dlp](https://github.com/yt-dlp/yt-dlp)。可用 `uv tool install yt-dlp` 安装下载工具；版本更新可用 `uv tool upgrade yt-dlp`。
3. 在 Agent 中输入：

> 使用 creator-methodology，提取这个 YouTube Shorts 链接的中文逐字稿，保留时间戳。先报告字幕情况，无字幕时转录音频，输出到我指定的目录。

只需提供链接和输出位置；频道批量任务还需指定日期范围。已有本地音频时可直接交给 Agent。执行期间电脑需保持运行；下载、依赖安装和首次模型获取需要网络。

如果只想先看输出格式，打开 [原创合成示例](examples/output/逐期/20261005%20-%20示例%20%5BdEmO0000001%5D.md)。该示例不是任何真实视频的逐字稿，不证明转录准确率。

开发者/熟悉终端的使用者见 [操作流程](references/workflow.md)。普通使用者可以让 Agent 完成这些步骤。

## 数据、费用与隐私

音频和字幕保存在使用者指定的本地工作目录；成品在指定的输出目录。可复制备份、迁移或自行删除；软件不提供自动清理或云端同步。YouTube 获取会向 YouTube 发出请求，首次下载模型/依赖会访问相应服务。本地 Whisper 推理不需要转录 API 密钥；Agent 阅读与提炼可能使用其云端模型并产生用量，隐私边界由所用 Agent 决定。

不把下载内容、账号 cookies、私人知识库或真实完整逐字稿提交到这个项目。只处理有权访问和处理的素材；分享第三方原文前另行确认权限。

## 可信度边界

- 网络/解析失败必须记录为“无法确认”，不能推断无字幕；确实无字幕仍可走音频转录。
- 时间轴末端对齐、密度和退化检查只是异常信号，不是逐句准确率证明。静音、音乐、数字列表和短视频可能触发误报。
- 术语映射只用于确认过的误识别，不能把创作者原话改成研究者自己的结论。
- 文件索引和时间戳校验只证明引用能定位，不证明结论成立。
- 不承诺任何视频都能下载或转录。私人/删除/地区或访问限制的视频需报告阻碍，不绕过访问控制。
- 本版本不承诺转录速度或每期固定要点数量。历史个人案例不作为公开准确率指标。

## 反馈与维护

欢迎在 [GitHub Issues](https://github.com/Ausfin888/creator-methodology/issues) 提交安装、字幕、转录与输出反馈。报告问题时提供系统/芯片、工具版本、错误摘要及可公开的视频链接；不要附 cookies、密钥或私人逐字稿。维护者按时间处理反馈，不承诺响应时限。

## English overview

An Agent Skill for turning Chinese creator videos into timestamped transcripts and evidence-linked methodology notes. Caption-first, local MLX Whisper fallback on Apple Silicon, conservative term correction, diagnostic checks, and citation validation. SRT/VTT utilities are Python standard-library tools. This pre-release has offline checks only; live downloads, speech recognition accuracy, and fresh-machine setup remain unverified. Maintainer: [Ausfin888](https://github.com/Ausfin888). Licensed under [MIT](LICENSE), copyright 2026 Ausfin888.

Offline regression checks: `python3 -m unittest discover -s tests -v` from this folder.

See [SKILL.md](SKILL.md), [workflow](references/workflow.md), and [release status](references/release-status.md).
