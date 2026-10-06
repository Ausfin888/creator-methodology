---
name: creator-methodology
description: Extract timestamped transcripts from YouTube videos, Shorts or local audio, and optionally synthesize a creator's reusable methodology with source-linked notes. Use for video transcription or creator-methodology research; do not require synthesis when the user only wants a transcript.
---

# Creator Methodology

把视频转为可回溯的逐字稿；只在用户要求时提炼方法论。脚本路径相对于本技能目录，工作和输出目录由用户指定或使用当前项目内的 `work/`、`outputs/`。

## 选择模式与范围

- **逐字稿**：单条视频/Shorts/本地音频，仅转录、必要的纠错和检查。
- **单视频提炼**：完整逐字稿后追加方法论要点。短视频可能只有一条规则或没有规则，不凑数量。
- **频道方法论**：先盘点用户选定的范围，再读全量逐字稿、生成逐期要点、总纲与一致性分析。

已提供的信息不要重复询问。频道批量任务缺范围时先澄清，不能擅自下载整个频道。不要把技能视为对公开发布、知识库写入、消息发送或全局配置修改的授权。

## 字幕与转录

1. 读 [操作流程](references/workflow.md)，检查工具及支持环境。
2. 查看 manual 和 auto 字幕列表。选择原语言的人工字幕；没有合适人工字幕才选择原语言自动字幕。不要批量下载机器翻译轨。
3. yt-dlp 没有返回字幕列表可能是网络/客户端失败。可用 `audit_caps.py` 独立读取网页；读取/解析失败记为 unknown，不等同无字幕。网页验证本身也不是万能来源。
4. 确认没有合适字幕后获取音频；字幕状态 unknown 时，也可在用户授权范围内尝试音频路径，但报告 unknown。
5. 无字幕转录使用 Apple Silicon Mac 的 mlx-whisper，默认完整 `mlx-community/whisper-large-v3-mlx`；领域词表应简短、只包含已知词，不能写待生成的句子或虚构内容。其他环境先明确当前不支持该转录后端。
6. 不自动读取浏览器 cookies。遇到登录、验证、地区或访问限制时记录原因；不绕过访问控制。遵守工具的联网权限流程，不把沙盒网络失败当成视频不可用。

## 修正与检查

- 原始字幕/转录先备份。用 `fix_terms.py --dry-run --check-idempotent` 预览，再根据上下文确认修正；保留修改明细。词表按素材建立，不能沿用未经核验的中文同音替换。
- `qc.py` 支持 SRT/VTT，输出时间轴末端对齐、内容密度、复读及数字退化。异常时退出非零；无文件或缺元数据不能算通过。疑似英文串只是人工复核提示。
- 检查阈值偏向中文口播，短视频/音乐/静音/数字讲解需人工判断。末端对齐不等于语音覆盖率。报告误报原因或残余不确定性，不能承诺“零错误”。
- 复读退化可以用 `--no-condition --force` 重新转录，先保留上一版，明确文件范围。
- `clean_subs.py` 生成 Markdown、时间戳和视频元数据。记录字幕来源 `manual` / `auto` / `local-asr` / `unknown`。已存在的成品默认不覆盖，避免抹掉人工修正和要点。

## 提炼与证据

用户只要逐字稿时，在该阶段交付，不运行总纲校验。用户要求提炼时读 [提炼规则](references/extraction-rubric.md)：

- 阅读完整逐字稿，只提取实际存在的可复用规则及其适用前提。
- 原话、作者规则、研究者解释要区分。不得把模糊原话擅自强化成作者未说的数字/技术判据。
- 要点附 `[HH:MM:SS]`，指向正文已有时间戳；无法确认的词标记存疑。
- 多视频总纲优先用 `[video:VIDEO_ID]` 引用。旧 `[YYYYMMDD]` 只在同日唯一视频时使用；同一天多条视频不能靠日期区分。
- 对比主张的前提、时点和范围，不能仅凭不同表述认定矛盾。仅有视频语料时不能自行宣称外部预测已被证伪。
- 运行 `validate_index.py --out ...`；逐期要点、索引解析、引用覆盖、日期和时间戳检查都应通过。校验只检查引用结构，不证明语义正确。

## 交付

先提供可点击的成品入口，然后说明实际处理范围、来源方式、残余错误和未完成部分。处理记录应保留素材清单、失败项、原始数据位置、纠错记录及检查结果。部分失败不能静默消失；其余素材继续处理。

本技能是按请求运行的 Agent 工具，不是独立 App、自动后台监控或云服务。数据保持在指定本地目录，是否上传给云端 Agent 由执行工具决定。
