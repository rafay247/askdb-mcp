#!/usr/bin/env python3
"""Add narration audio to docs/media/ui-demo.mp4.

The video's captions are already burned into a black bar at the bottom by
the original recording tool (mirrored in ui-demo.srt as a sidecar) -- this
script only adds a spoken narration track, it does not touch subtitles.

Uses Piper (offline neural TTS) for narration and ffmpeg (via imageio-ffmpeg,
no system install needed) for muxing.

Usage:
    .venv/bin/python scripts/demo/build_video.py
    .venv/bin/python scripts/demo/build_video.py --voice en_US-ryan-high
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import wave
from pathlib import Path

import imageio_ffmpeg

from narration import SCRIPT

ROOT = Path(__file__).resolve().parents[2]
VOICES_DIR = Path(__file__).resolve().parent / "voices"
SRC_VIDEO = ROOT / "docs" / "media" / "ui-demo.mp4"
SRC_SRT = ROOT / "docs" / "media" / "ui-demo.srt"
OUT_VIDEO = ROOT / "docs" / "media" / "ui-demo.mp4"
WORKDIR = ROOT / "scripts" / "demo" / ".build"

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SAMPLE_RATE = 22050
MIN_LENGTH_SCALE = 0.7  # floor so speech doesn't get unnaturally fast


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def video_duration(path: Path) -> float:
    proc = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True)
    for line in proc.stderr.splitlines():
        line = line.strip()
        if line.startswith("Duration:"):
            h, m, s = line.split(",")[0].split(":")[1:]
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"Could not determine duration of {path}")


def synthesize(text: str, out_path: Path, model: Path, config: Path, length_scale: float) -> None:
    subprocess.run(
        [sys.executable, "-m", "piper", "-m", str(model), "-c", str(config),
         "-f", str(out_path), "--length-scale", str(length_scale)],
        input=text.encode("utf-8"), capture_output=True, check=True,
    )


def fit_line(text: str, target_duration: float, model: Path, config: Path, tmp: Path) -> Path:
    """Synthesize `text`, speeding it up (bounded) if it overruns its window."""
    length_scale = 1.0
    out = tmp
    for attempt in range(3):
        synthesize(text, out, model, config, length_scale)
        dur = wav_duration(out)
        if dur <= target_duration or length_scale <= MIN_LENGTH_SCALE:
            if dur > target_duration:
                print(f"  ! '{text[:40]}...' still {dur - target_duration:.2f}s over "
                      f"budget at floor speed; will overlap slightly into next segment")
            return out
        length_scale = max(MIN_LENGTH_SCALE, length_scale * (target_duration / dur))
    return out


def build_narration_track(model: Path, config: Path) -> Path:
    WORKDIR.mkdir(parents=True, exist_ok=True)
    clip_paths: list[Path] = []
    prev_end = 0.0
    for i, (start, end, text) in enumerate(SCRIPT):
        gap = max(0.0, start - prev_end)
        if gap > 0.01:
            gap_path = WORKDIR / f"gap_{i:02d}.wav"
            with wave.open(str(gap_path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(SAMPLE_RATE)
                w.writeframes(b"\x00\x00" * int(SAMPLE_RATE * gap))
            clip_paths.append(gap_path)

        clip = WORKDIR / f"line_{i:02d}.wav"
        fit_line(text, end - start, model, config, clip)
        clip_paths.append(clip)
        prev_end = start + wav_duration(clip)

    combined = WORKDIR / "narration.wav"
    with wave.open(str(combined), "wb") as out_wav:
        out_wav.setnchannels(1)
        out_wav.setsampwidth(2)
        out_wav.setframerate(SAMPLE_RATE)
        for p in clip_paths:
            with wave.open(str(p), "rb") as in_wav:
                out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))

    total = wav_duration(combined)
    print(f"Narration track built: {total:.2f}s across {len(SCRIPT)} lines")
    return combined


def mux(video: Path, audio: Path | None, out: Path) -> None:
    # NOTE: docs/media/ui-demo.mp4 already has its captions burned into a
    # black bar at the bottom (baked in by the original recording tool, and
    # mirrored in ui-demo.srt). Do not run the ffmpeg `subtitles` filter here
    # -- it would render a second, overlapping copy of the same text.
    filters = []

    if audio is not None:
        vdur = video_duration(video)
        adur = wav_duration(audio)
        if adur > vdur:
            pad = adur - vdur + 0.2  # small buffer so the last word isn't flush at the cut
            filters.append(f"tpad=stop_mode=clone:stop_duration={pad:.3f}")
            print(f"Narration ({adur:.2f}s) runs past video ({vdur:.2f}s); "
                  f"freezing final frame for {pad:.2f}s so nothing is clipped")

    cmd = [FFMPEG, "-y", "-i", str(video)]
    if audio is not None:
        cmd += ["-i", str(audio)]
    if filters:
        cmd += ["-vf", ",".join(filters)]
    if audio is not None:
        cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default="en_US-lessac-medium")
    args = parser.parse_args()

    model = VOICES_DIR / f"{args.voice}.onnx"
    config = VOICES_DIR / f"{args.voice}.onnx.json"
    if not model.exists():
        sys.exit(
            f"Voice model not found: {model}\n"
            f"Download it with:\n"
            f"  .venv/bin/python -m piper.download_voices "
            f"--download-dir scripts/demo/voices {args.voice}"
        )

    audio = build_narration_track(model, config)
    tmp_out = WORKDIR / "ui-demo.tmp.mp4"
    WORKDIR.mkdir(parents=True, exist_ok=True)
    mux(SRC_VIDEO, audio, tmp_out)
    tmp_out.replace(OUT_VIDEO)
    print(f"Wrote {OUT_VIDEO}")


if __name__ == "__main__":
    main()
