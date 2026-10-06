#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""转录后的术语纠正层。

Whisper 在中英混说的专业内容上，错误高度集中于两类：
  1. 专有名词/代码被听成近音的无效串（IGV→RGV、Meta→Manta）
  2. 中文同音字（抄底→朝底、抗跌→扛跌）
两类都是确定性的，用映射表修比调模型参数可靠。

原则：只收录在该领域语境下无歧义的映射。宁可漏改，不可错改。

用法:
  python fix_terms.py --dir <srt目录> --terms <terms.json> [--dry-run] [--check-idempotent]

=== 两个必须知道的坑 ===

【坑 1｜非幂等替换】
  `APL → AAPL` 这类「短串 → 含短串的长串」映射不是幂等的：
  第一遍 APL→AAPL，第二遍 AAPL 里的 APL 又被命中 → AAAAPL，跑三遍变 AAAAAPL。
  本脚本默认对每条 plain 映射做幂等自检（replace 后再 replace 一次，结果必须相同），
  不幂等的直接拒绝加载，并提示改写成 regex 负向断言：
      "APL" → "AAPL"            ✗ 非幂等
      /(?<!A)APL/ → "AAPL"      ✓ 幂等
      /A{3,}PL/ → "AAPL"        ✓ 兼作已损坏文本的修复

【坑 2｜Python 的 \\b 在中文旁边不工作】
  Python 3 正则默认 Unicode 模式，**CJK 字符属于 \\w**，因此汉字与英文字母之间
  不存在「词边界」。`\\bmanta\\b` 匹配不到「买manta的时候」里的 manta。
  写正则时不要依赖 \\b 做中英边界，改用负向断言或显式字符类。
"""
import argparse, collections, glob, json, os, re, sys


def load_terms(path, strict=True):
    d = json.load(open(os.path.expanduser(path), encoding="utf-8"))
    plain = {}
    for section in ("name", "ticker", "homophone", "scan"):
        for k, v in d.get(section, {}).items():
            if k in plain and plain[k] != v:
                print(f"⚠️  键冲突: {k!r} → {plain[k]!r} / {v!r}", file=sys.stderr)
            plain[k] = v
    bad = [(k, v) for k, v in plain.items() if k in v and k != v]
    if bad:
        msg = "非幂等映射（跑两遍会累积错误），请改写成 regex 负向断言:\n" + "\n".join(
            f"    {k!r} → {v!r}    建议: /(?<!{v[:len(v)-len(k)] or '.'})" f"{re.escape(k)}/ → {v!r}"
            for k, v in bad)
        if strict:
            raise SystemExit("✗ " + msg)
        print("⚠️  " + msg, file=sys.stderr)
    regex = [(r["pattern"], r["replace"]) for r in d.get("regex", [])]
    for pat, _ in regex:
        if r"\b" in pat:
            print(f"⚠️  正则 {pat!r} 含 \\b —— 中文旁边不生效（CJK 属于 \\w），"
                  f"请改用负向断言", file=sys.stderr)
    return plain, regex


def fix(text, plain, keys, regex):
    hits = collections.Counter()
    for k in keys:
        if k in text and plain[k] != k:
            n = text.count(k)
            text = text.replace(k, plain[k])
            hits[f"{k} → {plain[k]}"] += n
    for pat, rep in regex:
        text, n = re.subn(pat, rep, text)
        if n:
            hits[f"/{pat}/ → {rep}"] += n
    return text, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--terms", required=True)
    ap.add_argument("--glob", default="*.srt")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-nonidempotent", action="store_true",
                    help="降级为警告（不推荐）")
    ap.add_argument("--check-idempotent", action="store_true",
                    help="改完立即再跑一遍，确认第二遍零命中")
    a = ap.parse_args()

    plain, regex = load_terms(a.terms, strict=not a.allow_nonidempotent)
    # 长键优先，避免短键先命中造成部分替换
    keys = sorted(plain, key=len, reverse=True)

    files = sorted(glob.glob(os.path.join(os.path.expanduser(a.dir), a.glob)))
    total = collections.Counter()
    nfiles = 0
    second = collections.Counter()
    if not files:
        raise SystemExit("No matching subtitle files; no corrections performed")
    if a.check_idempotent:
        for p in files:
            original = open(p, encoding="utf-8").read()
            once, _ = fix(original, plain, keys, regex)
            twice, _ = fix(once, plain, keys, regex)
            if twice != once:
                raise SystemExit("Non-idempotent mapping for " + os.path.basename(p) + "; no files written")
    for p in files:
        t = open(p, encoding="utf-8").read()
        t2, hits = fix(t, plain, keys, regex)
        if hits:
            if not a.dry_run:
                open(p, "w", encoding="utf-8").write(t2)
            nfiles += 1
            total.update(hits)
        if a.check_idempotent:
            _, h2 = fix(t2, plain, keys, regex)
            second.update(h2)

    tag = "（dry-run，未写盘）" if a.dry_run else ""
    print(f"处理 {len(files)} 个文件，其中 {nfiles} 个有修正{tag}")
    if total:
        print(f"\n修正明细（共 {sum(total.values())} 处）:")
        for k, v in total.most_common():
            print(f"  {v:>4}x  {k}")
    if a.check_idempotent:
        if second:
            print(f"\n✗ 幂等性检查失败：第二遍仍命中 {sum(second.values())} 处")
            for k, v in second.most_common():
                print(f"  {v:>4}x  {k}")
            raise SystemExit(1)
        print("\n✓ 幂等性检查通过（第二遍零命中）")


if __name__ == "__main__":
    main()
