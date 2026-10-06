#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 .srt / .vtt 清洗成带 YAML frontmatter 的 Markdown 逐字稿。

- 去掉序号与时间戳块结构，合并断行为通顺段落
- 每段落保留一个 [HH:MM:SS] 锚点，方便回溯原片
- 元数据取自同名 .info.json
- 同时消费「YouTube 原生字幕」与「本地转录出的 srt」，两条路在这里汇合

用法: python clean_subs.py --dir <srt目录> --out <输出目录> [--source "频道名"]
"""
import argparse, json, os, re
from pathlib import Path

# 同时兼容 SRT (00:00:01,000) 与 WebVTT (00:00:01.000 / 00:01.000)
TS_RE = re.compile(
    r"(?:(\d+):)?(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(?:\d+:)?\d{2}:\d{2}[,.]\d{3}"
)
TAG_RE = re.compile(r"<[^>]+>")
# 语言优先级：人工中文 > 其它中文 > 英文
LANG_PRIORITY = [
    "zh-Hans", "zh-CN", "zh-Hans-CN", "zh", "zh-TW", "zh-Hant", "zh-HK",
    "en", "en-US", "en-GB",
]


def parse_srt(path):
    from subtitle_utils import read_cues
    cues = []
    for start, end, value in read_cues(path):
        if not cues or cues[-1][1] != value:
            cues.append((int(start), value))
    return cues


def join(a, b):
    """中文之间不加空格，含英文/数字边界时加空格。"""
    if not a:
        return b
    if re.search(r"[一-鿿　-〿，。！？；：、）】」』]$", a) and \
       re.match(r"^[一-鿿　-〿，。！？；：、（【「『]", b):
        return a + b
    return a + " " + b


def dedup_overlap(a, b):
    """去掉滚动字幕造成的头尾重叠（b 的开头是 a 的结尾）。"""
    maxlap = min(len(a), len(b), 40)
    for n in range(maxlap, 5, -1):
        if a.endswith(b[:n]):
            return b[n:]
    return b


def fmt_ts(sec):
    return "%02d:%02d:%02d" % (sec // 3600, (sec % 3600) // 60, sec % 60)


def to_paragraphs(cues, min_chars=180, max_chars=520):
    """合并 cue 成段落，返回 [(start_sec, paragraph_text), ...]"""
    paras, buf, buf_start = [], "", None
    END_PUNCT = "。！？!?…"
    for start, text in cues:
        if buf_start is None:
            buf_start = start
        text = dedup_overlap(buf, text)
        if not text:
            continue
        buf = join(buf, text)
        long_enough = len(buf) >= min_chars
        ends_sentence = buf and buf[-1] in END_PUNCT
        if (long_enough and ends_sentence) or len(buf) >= max_chars:
            paras.append((buf_start, buf.strip()))
            buf, buf_start = "", None
    if buf.strip():
        paras.append((buf_start or 0, buf.strip()))
    return paras


def yaml_escape(s):
    return json.dumps(str(s), ensure_ascii=False)


def pick_srt(stem, srt_map):
    for lang in LANG_PRIORITY:
        key = f"{stem}.{lang}"
        if key in srt_map:
            return srt_map[key], lang
    for key, p in sorted(srt_map.items()):      # 兜底：任何 zh 开头的
        if key.startswith(stem + ".") and ".zh" in key:
            return p, key.rsplit(".", 1)[-1]
    for key, p in sorted(srt_map.items()):
        if key.startswith(stem + "."):
            return p, key.rsplit(".", 1)[-1]
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--source", default="", help="写进 frontmatter 的频道名")
    ap.add_argument("--overwrite", action="store_true", help="Explicitly replace existing Markdown after backup")
    ap.add_argument("--subtitle-source", choices=["manual", "auto", "local-asr", "unknown"], default="unknown")
    a = ap.parse_args()

    SRC = Path(os.path.expanduser(a.dir))
    OUT = Path(os.path.expanduser(a.out))
    OUT.mkdir(parents=True, exist_ok=True)

    srt_map = {}
    for ext in (".vtt", ".srt"):              # .srt 优先覆盖 .vtt
        for p in SRC.glob("*" + ext):
            if p.name.startswith("_"):        # 人工基准等留证文件不参与
                continue
            srt_map[p.name[: -len(ext)]] = p  # key = "日期 - 标题.zh"

    infos = sorted(SRC.glob("*.info.json"))
    report = []
    for ij in infos:
        stem = ij.name[: -len(".info.json")]
        meta = json.loads(ij.read_text(encoding="utf-8", errors="replace"))
        if meta.get("_type") == "playlist":
            continue
        target = OUT / f"{stem}.md"
        if target.exists() and not a.overwrite:
            print(f"保留已有成品: {target.name}")
            continue
        srt, lang = pick_srt(stem, srt_map)
        if srt is None:
            report.append((stem, meta.get("id"), None, 0, 0))
            continue
        cues = parse_srt(srt)
        if not cues:
            raise SystemExit(f"无可读字幕，未生成成品: {srt.name}")
        paras = to_paragraphs(cues)
        dur = meta.get("duration") or 0
        ud = meta.get("upload_date", "") or ""
        vid = str(meta.get("id", ""))
        url = meta.get("webpage_url") or ("https://www.youtube.com/watch?v=" + vid if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid) else "local-source:" + stem)
        head = [
            "---",
            f"title: {yaml_escape(meta.get('title',''))}",
            f"date: {yaml_escape(ud[:4]+'-'+ud[4:6]+'-'+ud[6:] if len(ud)==8 else '')}",
            f"duration: {yaml_escape(fmt_ts(int(dur)))}",
            f"duration_minutes: {round(dur/60, 1)}",
            f"url: {yaml_escape(url)}",
            f"video_id: {yaml_escape(meta.get('id',''))}",
            f"subtitle_lang: {lang}",
            f"source: {yaml_escape(a.source or meta.get('uploader',''))}",
            f"subtitle_source: {a.subtitle_source}",
            "---",
            "",
            f"# {meta.get('title','')}",
            "",
            "## 逐字稿",
            "",
        ]
        body = []
        for start, text in paras:
            body.append(f"**[{fmt_ts(start)}]** {text}")
            body.append("")
        (OUT / f"{stem}.md").write_text("\n".join(head + body), encoding="utf-8")
        report.append((stem, meta.get("id"), lang, len(paras),
                       sum(len(t) for _, t in paras)))

    if not infos:
        raise SystemExit("未找到 metadata，未生成成品")

    print(f"info.json: {len(report)}  srt files: {len(srt_map)}  md written: "
          f"{sum(1 for r in report if r[2])}")
    missing = [r for r in report if not r[2]]
    if missing:
        print("\n无字幕的期数:")
        for stem, vid, *_ in missing:
            print(f"  - {stem}  (id={vid})")
    print("\n明细 (期 / 语言 / 段落数 / 字数):")
    for stem, vid, lang, np_, nc in report:
        print(f"  {stem[:60]:<62} {str(lang):<10} {np_:>4}  {nc:>7}")

    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
