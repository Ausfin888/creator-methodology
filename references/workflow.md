# 操作流程：单视频优先，批量沿用同一目录约定

以下命令从技能目录执行。示例视频链接需替换为实际有权处理的链接。路径包含空格时保留引号。只执行用户授权的任务；此文档不会授予外部发布或账号访问权限。

## 环境

Python 3.11+；字幕与检查脚本只依赖标准库。下载需要 yt-dlp。无字幕转录额外需要 Apple Silicon Mac、uv、mlx-whisper、av、numpy。uv 首次运行可能下载 Python/依赖，Whisper 首次运行会获取模型，磁盘空间和时间以实际下载为准。

```bash
python3 --version
yt-dlp --version
uv --version
```

若未安装 yt-dlp，按官方安装说明处理：<https://github.com/yt-dlp/yt-dlp>。MLX Whisper 来源：<https://github.com/ml-explore/mlx-examples/tree/main/whisper>。

## 1. 查看字幕与元数据

```bash
mkdir -p work/video/audio outputs/video/逐期
yt-dlp --no-playlist --skip-download --write-info-json --list-subs \
  -o 'work/video/%(upload_date)s - %(title)s [%(id)s].%(ext)s' \
  'https://www.youtube.com/shorts/VIDEO_ID'
```

同日多个视频用 `VIDEO_ID` 区分文件。metadata 用原来源日期，不能随意猜测缺失日期。失败时报告失败；不能把空目录解释为无字幕。单条 Shorts 可用同一 ID 的 `/watch?v=VIDEO_ID` 链接。

## 2. 选择一个确实存在的原语言字幕轨

例如列表确认存在 `zh-Hans` 人工字幕后：

```bash
yt-dlp --no-playlist --skip-download --write-info-json --write-subs \
  --sub-langs 'zh-Hans' --sub-format 'vtt/srt/best' --sleep-requests 3 \
  -o 'work/video/%(upload_date)s - %(title)s [%(id)s].%(ext)s' \
  'https://www.youtube.com/watch?v=VIDEO_ID'
```

自动字幕只在确认列表中原语言轨的准确代码后，用 `--write-auto-subs` 替代 `--write-subs`，把 `--sub-langs` 改成那个精确代码。不要使用 `all` 或下载整批机器翻译轨。重试应针对已发现的原因，不无限重复请求。

独立检查（读取结果包括 present / absent / unknown）：

```bash
python3 scripts/audit_caps.py --dir work/video
```

若播放器响应无法取得或解析，结果是 unknown。只有正常响应明确提供字幕数组或正常可播放响应没有该字段，才报告该来源的状态；双路径不一致保留冲突。

## 3. 没有字幕：下载音频并转录

```bash
yt-dlp --no-playlist --write-info-json \
  -f 'bestaudio[ext=m4a]/bestaudio' --sleep-requests 3 \
  -o 'work/video/audio/%(upload_date)s - %(title)s [%(id)s].%(ext)s' \
  'https://www.youtube.com/watch?v=VIDEO_ID'
```

把 audio 目录内的 `.info.json` 复制到 `work/video/`，供质检和清洗匹配同名音频；不改写其来源日期。直接下载音频轨，不强制重封装，所以无需系统 ffmpeg；PyAV 负责解码。已取得的本地音频也可放进 `audio/`，但需创建同名、明确标注本地来源的 metadata，不能伪造 YouTube ID。

参考 `examples/prompt.txt` 为实际素材编写简短词表：

```bash
uv run --python 3.11 --with mlx-whisper --with av --with numpy \
  python scripts/transcribe.py --dir work/video --prompt-file work/video/prompt.txt
```

输出 `.zh.srt`。失败退出非零；无待处理文件会报告跳过状态。`--force` 覆盖前先备份，`--only` 缩小范围，`--no-condition` 用于复读问题。

## 4. 修正、诊断和清洗

保留原始字幕和音频，然后预览并确认术语映射：

```bash
python3 scripts/fix_terms.py --dir work/video --glob '*.srt' \
  --terms work/video/terms.json --dry-run --check-idempotent
python3 scripts/fix_terms.py --dir work/video --glob '*.srt' \
  --terms work/video/terms.json --check-idempotent
python3 scripts/qc.py --dir work/video
python3 scripts/clean_subs.py --dir work/video --out outputs/video/逐期 \
  --subtitle-source local-asr
```

VTT 时将 `--glob '*.srt'` 改成 `--glob '*.vtt'`。来源按本轮实际情况选 manual / auto / local-asr / unknown；混合来源目录需分批处理，不能把全批设为同一种。检查报警必须解释/处理，不能修改阈值只为“通过”。重跑 cleaner 默认跳过已有 Markdown；确需重新生成使用 `--overwrite` 并备份成品。

## 5. 可选的方法论

Agent 读全部逐字稿，追加要点和时间戳，生成总纲，再执行：

```bash
python3 scripts/validate_index.py --out outputs/video
```

只要逐字稿无需总纲；同日多视频必须使用 `[video:VIDEO_ID]`。全部结果、失败项和未确认项写进处理记录。`qc-report.json` 和命令输出是后台审计记录，逐字稿/总纲是主要用户输出。

## 无网络的示例检查

```bash
python3 scripts/qc.py --dir examples/input
python3 scripts/validate_index.py --out examples/output
```

这些命令验证合成样本和引用规则，不测试真实视频下载或语音识别。示例不应该用于宣传真实转录准确率。
