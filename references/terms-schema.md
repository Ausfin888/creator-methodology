# 术语映射

`name` / `ticker` / `homophone` / `scan` 为字符串映射，`regex` 为 pattern/replace 数组。见 `examples/terms.json`，这是教学示例，不是实际素材词表。

先按素材建立词表、读上下文，保留原文，再用 dry-run 检查。只有确认的误识别才修；存疑词原样保留并标记。映射必须两次应用结果一致。正则的 `\b` 不能可靠表示中英边界，优先明确上下文。

`fix_terms.py --check-idempotent` 会在写入任何文件之前检查当前输入的二次替换；失败不会写入这批文件。该检查只覆盖实际输入文本，不证明所有可能句子都安全。
