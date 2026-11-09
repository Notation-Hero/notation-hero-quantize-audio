# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Notation Hero
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["numpy", "soundfile"]
# ///
"""A check that doesn't use the beat detector: the drum hits of a drum stem against a steady grid.

Every strong onset is snapped to the nearest 16th note of t0 + k * 60 / bpm and its distance kept.
Prints the median and 95th percentile in ms, overall and per 16 bars.

  uv run check_drums.py "song - quantized/drums-87bpm.wav" --bpm 87 --t0 1.23 [--from 0 --to 300]
  uv run check_drums.py --selftest     (Rubber Band's own accuracy on a synthetic click track)
"""
import argparse, subprocess, tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44100


def onsets(path: Path) -> np.ndarray:
    y, sr = sf.read(path)
    y = y.mean(1) if y.ndim > 1 else y
    hop, win = 128, 1024
    frames = np.lib.stride_tricks.sliding_window_view(y, win)[::hop] * np.hanning(win)
    mag = np.log1p(10 * np.abs(np.fft.rfft(frames, axis=1)))
    flux = np.maximum(0, np.diff(mag, axis=0)).sum(1)
    flux = (flux - np.median(flux)) / (np.percentile(flux, 99) + 1e-9)
    peaks = [i for i in range(2, len(flux) - 2) if flux[i] > 0.25 and flux[i] == flux[i - 2: i + 3].max()]
    # refine each peak to the sample where the energy rises fastest
    t = []
    for i in peaks:
        a, b = max(0, (i - 2) * hop), (i + 4) * hop
        env = np.convolve(np.abs(y[a:b]), np.ones(32) / 32, "same")
        t.append((a + int(np.argmax(np.diff(env)))) / sr)
    t = np.array(t)
    return t[np.concatenate([[True], np.diff(t) > 0.05])]


def errors(t: np.ndarray, t0: float, bpm: float):
    step = 60 / bpm / 4
    k = np.round((t - t0) / step)
    return k, (t - (t0 + k * step)) * 1000


def summary(name, t, t0, bpm, lo, hi):
    sel = (t >= lo) & (t <= hi)
    k, e = errors(t[sel], t0, bpm)
    off = np.median(e)
    a = np.abs(e - off)
    print(f"{name}: {len(a)} hits, offset {off:+.1f} ms, jitter median {np.median(a):.1f} ms, p95 {np.percentile(a, 95):.1f} ms")
    bars = (k // 16).astype(int)
    row = []
    for b in range(bars.min(), bars.max() + 1, 16):
        m = (bars >= b) & (bars < b + 16)
        if m.sum() > 8:
            row.append(f"bars {b + 1}-{b + 16}: {np.median(a[m]):.0f}")
    print("   median ms per 16 bars:", ", ".join(row))


def selftest():
    bpm, n = 90.0, 200
    period = 60 / bpm
    wobble = np.cumsum(period * (1 + 0.03 * np.sin(np.arange(n) / 7)))
    src_t = 1.0 + np.concatenate([[0], wobble[:-1]])
    y = np.zeros(int((src_t[-1] + 2) * SR))
    click = np.sin(2 * np.pi * 2000 * np.arange(400) / SR) * np.exp(-np.arange(400) / 60)
    for t in src_t:
        i = int(t * SR); y[i: i + 400] += click
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        sf.write(d / "in.wav", np.stack([y, y], 1), SR)
        tgt = 1.0 + np.arange(n) * period
        pairs = [(0, 0)] + list(zip(src_t, tgt))
        (d / "tm.txt").write_text("".join(f"{round(s * SR)} {round(t * SR)}\n" for s, t in pairs))
        total = tgt[-1] + (len(y) / SR - src_t[-1])
        subprocess.run(["rubberband", "-q", "--fine", "-M", str(d / "tm.txt"), "-D", f"{total:.6f}", str(d / "in.wav"), str(d / "out.wav")], check=True)
        before, after = onsets(d / "in.wav"), onsets(d / "out.wav")
    print("self-test: a click track wobbling ±3% around 90 bpm, flattened to 90")
    summary(" before", before, 1.0, bpm, 0, 1e9)
    summary(" after ", after, 1.0, bpm, 0, 1e9)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("wav", nargs="?", type=Path)
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--t0", type=float)
    ap.add_argument("--from", dest="lo", type=float, default=0)
    ap.add_argument("--to", dest="hi", type=float, default=1e9)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        summary(a.wav.name, onsets(a.wav), a.t0, a.bpm, a.lo, a.hi)
