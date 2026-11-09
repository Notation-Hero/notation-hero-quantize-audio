# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Notation Hero
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["numpy", "soundfile", "mido", "beat-this", "torch", "soxr", "einops", "rotary-embedding-torch"]
# ///
"""notation-hero-quantize-audio: quantize a whole recording onto one steady tempo, so the song plays
over a fixed metronome or click track. Stems and vocals included, pitch kept.

The beats come from one of three places:
  auto          detected from the audio (Beat This!, MIT, offline)
  chart:FILE    a rhythm-game chart's notes.mid, whose tempo map was placed by hand on this recording
  gp:FILE       a Guitar Pro 8 file's sync points (bar -> time in its embedded recording)
  gp+auto:FILE  the detected beats, each numbered by where the sync points say it falls

Each beat is moved to start + n * 60 / bpm, and Rubber Band (the `rubberband` command, run as a separate
program) stretches the audio between beats with the pitch kept. Every stem gets the same time map, so they
stay locked together. The beats of the result are then detected again and measured against the grid.

  quantize-audio --bpm 87 song.mp3 [stem.wav ...]        (or: uv run quantize_audio.py ...)

Writes "<song> - quantized/" next to the song: the quantized song and each stem as MP3 (320 kbps; --wav adds WAV
copies), and report.json.
--click adds before/after previews with a metronome over them, to hear the difference.
"""
import argparse, json, re, shutil, statistics, subprocess, sys, zipfile
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44100


def decode(src: Path, dst: Path) -> Path:
    """Any audio file -> 44.1 kHz stereo WAV."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ar", str(SR), "-ac", "2", str(dst)], check=True)
    return dst


_f2b = None


def detect(wav: Path) -> np.ndarray:
    global _f2b
    if _f2b is None:
        import torch
        from beat_this.inference import File2Beats
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
        _f2b = File2Beats(checkpoint_path="final0", device=dev, dbn=False)
    beats, _downbeats = _f2b(str(wav))
    return np.asarray(beats, dtype=float)


def number_beats(beats: np.ndarray, bpm: float | None = None) -> list[tuple[float, float]]:
    """(time, beat number) for detected beats. With the song's tempo known, a beat closer than 3/4 of a beat
    to the last one kept is dropped (the detector went to eighths there) and a long gap counts its missed beats.
    Without it, the local median gap stands in for the beat."""
    gaps = np.diff(beats)
    out, n, last = [(beats[0], 0.0)], 0.0, beats[0]
    for i in range(1, len(beats)):
        period = 60 / bpm if bpm else statistics.median(gaps[max(0, i - 9): i + 7])
        g = beats[i] - last
        if g < 0.75 * period:
            continue
        n += round(g / period)
        out.append((beats[i], n))
        last = beats[i]
    return drop_glitches(out, bpm) if bpm else out


def drop_glitches(anchors, bpm: float, limit=0.08):
    """Drop a beat when the tempo to both its neighbours is more than 8% off the song's tempo:
    a detector slip, not the band. The stretch then runs straight through it."""
    keep = list(anchors)
    changed = True
    while changed and len(keep) > 2:
        changed = False
        bpms = [60 * (n2 - n1) / (t2 - t1) for (t1, n1), (t2, n2) in zip(keep, keep[1:])]
        for i in range(1, len(keep) - 1):
            if abs(bpms[i - 1] / bpm - 1) > limit and abs(bpms[i] / bpm - 1) > limit:
                del keep[i]; changed = True
                break
    return keep


def chart_beats(mid: Path, length: float) -> list[tuple[float, float]]:
    """Every quarter note of a chart's tempo map, as (time, beat number)."""
    import mido
    m = mido.MidiFile(str(mid))
    tpb = m.ticks_per_beat
    tempos, tick = [(0, 500000)], 0
    for msg in m.tracks[0]:
        tick += msg.time
        if msg.type == "set_tempo":
            tempos.append((tick, msg.tempo))
    out, beat = [], 0
    while True:
        t_tick = beat * tpb
        sec, prev_tick, prev_tempo = 0.0, 0, tempos[0][1]
        for tk, tp in tempos[1:]:
            if tk > t_tick:
                break
            sec += (tk - prev_tick) / tpb * prev_tempo / 1e6
            prev_tick, prev_tempo = tk, tp
        sec += (t_tick - prev_tick) / tpb * prev_tempo / 1e6
        if sec > length:
            return out
        out.append((sec, float(beat)))
        beat += 1


def gp_beats(gp: Path) -> tuple[list[tuple[float, float]], float, Path]:
    """A Guitar Pro 8 file's sync points as (time in its recording, beat number at bar start).
    Returns the anchors, the file's own tempo and the embedded recording, extracted next to the output."""
    z = zipfile.ZipFile(gp)
    x = z.read("Content/score.gpif").decode("utf-8")
    if "<Repeat " in x or "<Jump" in x:
        sys.exit("gp: repeats and jumps are not handled in this spike")
    pad = re.search(r"<FramePadding>(-?\d+)</FramePadding>", x)
    pad = int(pad.group(1)) if pad else 0
    quarters = []
    for mb in re.findall(r"<MasterBar>(.*?)</MasterBar>", x, re.S):
        num, den = map(int, re.search(r"<Time>(\d+)/(\d+)</Time>", mb).groups())
        quarters.append(num * 4 / den)
    start = np.concatenate([[0], np.cumsum(quarters)])
    tempo, anchors = None, []
    for a in re.findall(r"<Automation>(.*?)</Automation>", x, re.S):
        bar = int(re.search(r"<Bar>(\d+)</Bar>", a).group(1))
        if "<Type>Tempo</Type>" in a and tempo is None:
            tempo = float(re.search(r"<Value>([\d.]+)", a).group(1))
        if "<Type>SyncPoint</Type>" in a:
            frame = float(re.search(r"<FrameOffset>([\d.-]+)</FrameOffset>", a).group(1))
            anchors.append(((frame - pad) / SR, float(start[bar])))
    asset = next(n for n in z.namelist() if n.startswith("Content/Assets/") and not n.endswith("/"))
    return sorted(anchors), tempo, asset


def refine(coarse, beats: np.ndarray) -> list[tuple[float, float]]:
    """Number each detected beat by the coarse map (sync points); keep those within a quarter beat of a whole number."""
    t = np.array([a for a, _ in coarse]); n = np.array([b for _, b in coarse])
    inside = beats[(beats >= t[0]) & (beats <= t[-1])]
    est = np.interp(inside, t, n)
    out, seen = [], set()
    for b, e in zip(inside, est):
        k = round(e)
        if abs(e - k) < 0.25 and k not in seen:
            out.append((float(b), float(k))); seen.add(k)
    return out


def time_map(anchors, bpm: float, length: float):
    """Source -> target seconds. The first anchor stays put; each later beat lands on the grid.
    Before the first anchor and after the last, the audio plays at its own speed."""
    period = 60.0 / bpm
    t0, n0 = anchors[0]
    pairs = [(t, t0 + (n - n0) * period) for t, n in anchors if t > 0]  # Rubber Band reads a 0 0 line as a 0/0 ratio
    last_src, last_tgt = pairs[-1]
    return pairs, last_tgt + (length - last_src), (t0, n0)


def stretch(wav: Path, pairs, total: float, dst: Path, engine="crisp"):
    tm = dst.with_suffix(".timemap.txt")  # dst is in the work folder
    tm.write_text("".join(f"{round(s * SR)} {round(t * SR)}\n" for s, t in pairs))
    opts = ["--fine", "--centre-focus"] if engine == "fine" else ["--crisp", "6"]
    subprocess.run(["rubberband", "-q", *opts, "-M", str(tm), "-D", f"{total:.6f}", str(wav), str(dst)], check=True)


def grid_error(beats: np.ndarray, t0: float, period: float, end: float, offbeats=False) -> dict:
    """How far each detected beat between t0 and end sits from the grid t0 + k * period, in ms.
    offset: the median signed distance (one number for the whole song, which a song's start offset fixes);
    jitter: the median and 95th percentile distance from that offset, which is what a metronome player hears.
    The worst ones are listed with their bar and beat (bar 1 = the first anchor's bar)."""
    beats = beats[(beats >= t0 - period / 2) & (beats <= end + period / 2)]
    phase = (beats - t0) / period
    err = (phase - np.round(phase)) * period * 1000
    skipped = 0
    if offbeats:
        # after the stretch, a detection over a quarter beat from the grid is the detector marking an "&",
        # not a beat a quarter beat late (the stretch can't put one there): count them apart
        on = np.abs(err) <= period * 250
        skipped = int((~on).sum()); beats, phase, err = beats[on], phase[on], err[on]
    off = float(np.median(err))
    a = np.abs(err - off)
    worst = [{"t": round(float(beats[i]), 2), "bar": int(np.round(phase[i]) // 4) + 1, "beat": int(np.round(phase[i]) % 4) + 1,
              "ms": round(float(err[i] - off), 1)} for i in np.argsort(-a)[:8]]
    return {"offset_ms": round(off, 1), "jitter_median_ms": round(float(np.median(a)), 1), "jitter_p95_ms": round(float(np.percentile(a, 95)), 1),
            "max_ms": round(float(a.max()), 1), "beats": int(len(a)), "offbeat_detections": skipped, "worst": worst}


def best_grid_error(beats: np.ndarray) -> dict:
    """The recording as it is: its beats against the steady tempo that fits them best."""
    numbered = number_beats(beats)
    t = np.array([b for b, _ in numbered]); n = np.array([k for _, k in numbered])
    k, c = np.polyfit(n, t, 1)
    err = np.abs(t - (k * n + c)) * 1000
    return {"bpm_fit": round(60 / k, 2), "median_ms": round(float(np.median(err)), 1), "p95_ms": round(float(np.percentile(err, 95)), 1), "max_ms": round(float(err.max()), 1)}


def bar_tempos(anchors, per_bar=4) -> list[float]:
    """The played tempo of each bar (4 beats) from the anchors."""
    t = np.array([a for a, _ in anchors]); n = np.array([b for _, b in anchors])
    edges = np.arange(n[0], n[-1], per_bar)
    times = np.interp(edges, n, t)
    return [round(60 * per_bar / d, 1) for d in np.diff(times)]


def click(length: float, t0: float, period: float, dst: Path, per_bar=4):
    y = np.zeros(int(length * SR) + SR)
    tick = np.sin(2 * np.pi * np.arange(int(0.03 * SR)) / SR * 1500) * np.exp(-np.arange(int(0.03 * SR)) / (0.006 * SR))
    k = 0
    while t0 + k * period < length:
        i = int((t0 + k * period) * SR)
        y[i: i + len(tick)] += tick * (0.9 if k % per_bar == 0 else 0.5)
        k += 1
    sf.write(dst, np.stack([y, y], 1)[: int(length * SR)], SR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", nargs="+", type=Path, help="the mix first, then any stems (same length)")
    ap.add_argument("--beats", default="auto", help="auto (default) | chart:notes.mid | gp:file.gp | gp+auto:file.gp")
    ap.add_argument("--bpm", type=float, help="target tempo (default: the gp file's tempo, else the fitted one)")
    ap.add_argument("--out", type=Path, help='output folder (default: "<song> - quantized" next to the song)')
    ap.add_argument("--click", action="store_true", help="also write before/after previews with a metronome over them")
    ap.add_argument("--no-check", action="store_true", help="skip measuring the result (saves a minute)")
    ap.add_argument("--keep-work", action="store_true", help="keep the work folder (decoded inputs, time maps)")
    ap.add_argument("--wav", action="store_true", help="also write each result as WAV (lossless) beside its MP3")
    ap.add_argument("--every", type=int, default=1, help="keep one key point every N beats (4 = one per bar in 4/4)")
    ap.add_argument("--engine", choices=["crisp", "fine"], default="crisp", help="Rubber Band's R2 engine with crisp transients (best in the spike), or R3")
    a = ap.parse_args()
    if a.out is None:
        first = Path(a.beats.split(":", 1)[1]) if a.beats.startswith(("gp:", "gp+auto:")) else a.audio[0]
        a.out = first.resolve().parent / f"{first.stem} - quantized"
    if a.beats == "auto" and a.bpm is None:
        print("note: no --bpm given; using the tempo that fits the recording best. Give the song's BPM for the best result.")
    a.out.mkdir(parents=True, exist_ok=True)
    work = a.out / "work"; work.mkdir(exist_ok=True)

    gp_tempo = None
    if a.beats.startswith(("gp:", "gp+auto:")):
        gp = Path(a.beats.split(":", 1)[1])
        anchors, gp_tempo, asset = gp_beats(gp)
        emb = work / Path(asset).name
        emb.write_bytes(zipfile.ZipFile(gp).read(asset))
        a.audio = [emb] + [p for p in a.audio if p.name != "-"]
    wavs = [decode(p, work / f"{i:02d}-{p.stem}.wav") for i, p in enumerate(a.audio)]
    length = sf.info(wavs[0]).duration

    src_beats = detect(wavs[0])
    report = {"source": a.beats, "every": a.every, "engine": a.engine, "length_s": round(length, 2), "before_auto": best_grid_error(src_beats)}
    if a.beats == "auto":
        anchors = number_beats(src_beats, a.bpm)
    elif a.beats.startswith("chart:"):
        anchors = chart_beats(Path(a.beats[6:]), length)
    else:
        if len(anchors) < 2:
            sys.exit(f"gp: only {len(anchors)} sync point(s); the file says nothing about where the beats are")
        if a.beats.startswith("gp+auto:"):
            anchors = refine(anchors, src_beats)
    bpm = a.bpm or gp_tempo or report["before_auto"]["bpm_fit"]
    tempos = bar_tempos(anchors)
    report |= {"t0": round(float(anchors[0][0]), 4), "target_bpm": bpm, "anchors": len(anchors), "bar_tempo_min": min(tempos), "bar_tempo_max": max(tempos),
               "bar_tempo_median": statistics.median(tempos)}

    if a.every > 1:
        n0 = anchors[0][1]
        anchors = [x for x in anchors if (x[1] - n0) % a.every == 0] + ([anchors[-1]] if (anchors[-1][1] - n0) % a.every else [])
    pairs, total, (t0, _) = time_map(anchors, bpm, length)
    outs = []
    for w in wavs:
        dst = work / (w.stem[3:] + f"-{bpm:g}bpm.wav")
        stretch(w, pairs, total, dst, a.engine)
        outs.append(dst)
    period = 60 / bpm
    for o in outs:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(o), "-b:a", "320k", str(a.out / (o.stem + ".mp3"))], check=True)
        if a.wav:
            shutil.copy2(o, a.out / o.name)
    if a.click:
        click(total, t0, period, work / "click.wav")
        for name, song in (("after", outs[0]), ("before", wavs[0])):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(song), "-i", str(work / "click.wav"), "-filter_complex",
                            "[0][1]amix=inputs=2:weights=1 0.6:normalize=0:duration=first", "-b:a", "192k",
                            str(a.out / f"{name}-with-click-{bpm:g}.mp3")], check=True)
    if not a.no_check:
        report["after_vs_grid"] = grid_error(detect(outs[0]), t0, period, pairs[-1][1], offbeats=True)
        report["before_vs_grid"] = grid_error(src_beats, t0, period, pairs[-1][0])
        lens = {o.stem + ".mp3": round(sf.info(o).duration, 3) for o in outs}
        report["output_lengths_s"] = lens
    b = report.get("before_vs_grid")
    if b:
        report["verdict"] = ("already steady: play it as it is, with a start offset of %+.0f ms" % b["offset_ms"]
                             if b["jitter_p95_ms"] < 30 else "drifts: use the quantized file")
    report["bar_tempos"] = tempos
    (a.out / "report.json").write_text(json.dumps(report, indent=1))
    if not a.keep_work:
        shutil.rmtree(work)
    files = [o.stem + ".mp3" for o in outs]
    print(f"\n{a.out}\n  " + "\n  ".join(files) + ("\n  (and each as WAV)" if a.wav else ""))
    print(f"  tempo {bpm:g} BPM; the band played {min(tempos)}-{max(tempos)}")
    if "after_vs_grid" in report:
        b, af = report["before_vs_grid"], report["after_vs_grid"]
        print(f"  off the beat (typical / worst 5%): before {b['jitter_median_ms']:.0f} / {b['jitter_p95_ms']:.0f} ms,"
              f" after {af['jitter_median_ms']:.0f} / {af['jitter_p95_ms']:.0f} ms")
        print(f"  {report['verdict']}")


if __name__ == "__main__":
    main()
