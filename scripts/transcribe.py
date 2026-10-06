#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 mlx-whisper large-v3 把 <dir>/audio/*.m4a 转成 <dir>/*.zh.srt，供 clean_subs.py 消费。

- 解码走 PyAV（wheel 自带 ffmpeg 库），不依赖系统 ffmpeg
- 可断点续跑：已存在同名 .zh.srt 的直接跳过
- initial_prompt 注入领域术语表，压中英混说的识别错误
- --no-condition 用于修复复读循环（condition_on_previous_text=False）

用法:
  uv run --with mlx-whisper --with av python transcribe.py --dir ~/Downloads/xxx-subs \
      --prompt-file ~/Downloads/xxx-subs/_prompt.txt
  # 单期重转修复复读:
  ... python transcribe.py --dir ... --only 20250911 --no-condition --force
"""
import argparse, glob, os, time



MODEL = "mlx-community/whisper-large-v3-mlx"   # 完整 large-v3，非 turbo / 非量化


def load_audio(path, sr=16000):
    """m4a -> 16k 单声道 float32 numpy，不经过系统 ffmpeg。"""
    with av.open(path) as container:
        stream = container.streams.audio[0]
        stream.thread_type = "AUTO"
        resampler = av.audio.resampler.AudioResampler(
            format="fltp", layout="mono", rate=sr)
        chunks = []
        for frame in container.decode(stream):
            for f in resampler.resample(frame):
                chunks.append(f.to_ndarray().reshape(-1))
        for f in resampler.resample(None):        # flush
            chunks.append(f.to_ndarray().reshape(-1))
    if not chunks:
        raise RuntimeError("no audio decoded: " + path)
    return np.concatenate(chunks).astype(np.float32)


def ts(sec):
    total = int(round(sec * 1000))
    whole, ms = divmod(total, 1000)
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments, path):
    out = []
    for i, seg in enumerate(segments, 1):
        text = seg["text"].strip()
        if not text:
            continue
        out.append(f"{i}\n{ts(seg['start'])} --> {ts(seg['end'])}\n{text}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--prompt-file", help="领域术语表 initial_prompt，强烈建议提供")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", help="文件名子串过滤，用于单期重转")
    ap.add_argument("--force", action="store_true", help="覆盖已有 srt")
    ap.add_argument("--no-condition", action="store_true",
                    help="condition_on_previous_text=False，修复复读循环")
    a = ap.parse_args()

    import platform
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("This transcription backend requires an Apple Silicon Mac")
    global np, av, mlx_whisper
    try:
        import numpy as np
        import av
        import mlx_whisper
    except ImportError:
        raise SystemExit("Missing dependencies: run via uv with mlx-whisper, av and numpy")
    root = os.path.expanduser(a.dir)
    audio_dir = os.path.join(root, "audio")
    prompt = ""
    if a.prompt_file:
        prompt = open(os.path.expanduser(a.prompt_file), encoding="utf-8").read().strip()
    else:
        print("!! 未提供 --prompt-file，专有名词识别率会明显下降", flush=True)

    files = sorted(sum((glob.glob(os.path.join(audio_dir, "*" + e))
                        for e in (".m4a", ".mp3", ".m4b", ".aac", ".opus", ".webm", ".wav", ".flac")), []))
    if a.only:
        files = [f for f in files if a.only in f]
    todo = []
    for f in files:
        stem = os.path.splitext(os.path.basename(f))[0]
        dst = os.path.join(root, f"{stem}.{a.lang}.srt")
        if not a.force and os.path.exists(dst) and os.path.getsize(dst) > 0:
            continue
        todo.append((f, dst, stem))
    if a.limit:
        todo = todo[: a.limit]

    if not files:
        raise SystemExit("No audio files matched; no transcription performed")
    if not todo:
        print("All matching transcripts already exist; skipped without revalidation")
        return
    print(f"待转录 {len(todo)} / 共 {len(files)} 个音频", flush=True)
    t_all = time.time()
    failed = []
    for i, (src, dst, stem) in enumerate(todo, 1):
        t0 = time.time()
        # 单个坏音频应记录失败，继续处理其余文件，末尾汇报失败状态。
        try:
            audio = load_audio(src)
        except Exception as e:
            failed.append((stem, f"解码失败 {type(e).__name__}: {e}"))
            print(f"[{i}/{len(todo)}] ❌ 跳过（音频损坏）{stem[:46]}", flush=True)
            continue
        dur = len(audio) / 16000
        try:
            r = mlx_whisper.transcribe(
                audio,
                path_or_hf_repo=a.model,
                language=a.lang,
                task="transcribe",
                initial_prompt=prompt or None,
                condition_on_previous_text=not a.no_condition,
                temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
                compression_ratio_threshold=2.4,
                logprob_threshold=-1.0,
                no_speech_threshold=0.6,
                word_timestamps=False,
                verbose=None,
            )
            if not r.get("segments"):
                raise ValueError("No speech segments returned")
            temp = dst + ".tmp"
            write_srt(r["segments"], temp)
            os.replace(temp, dst)
        except Exception as e:
            failed.append((stem, f"转录失败 {type(e).__name__}: {e}"))
            print(f"[{i}/{len(todo)}] 转录失败: {stem}", flush=True)
            continue
        el = time.time() - t0
        print(f"[{i}/{len(todo)}] {stem[:46]:<48} "
              f"{dur/60:5.1f}分 用时{el/60:5.1f}分 "
              f"({dur/el:4.1f}x) 段{len(r['segments']):4d}", flush=True)
    print(f"\n全部完成，总耗时 {(time.time()-t_all)/60:.1f} 分钟")
    if failed:
        print(f"\n⚠️  {len(failed)} 个音频损坏、未转录（检查失败原因后再处理）：")
        for stem, why in failed:
            print(f"   {stem}\n     {why}")

        raise SystemExit(1)


if __name__ == "__main__":
    main()
