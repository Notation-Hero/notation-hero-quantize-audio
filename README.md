# notation-hero-quantize-audio

**Quantize a whole song to a steady click.** Give it a recording (an MP3, a WAV, a full mix plus its stems), tell
it the song's BPM, and it moves every beat onto a perfect grid. The audio between beats is time-stretched with the
pitch kept. Bands rarely play at exactly one tempo: a song "at 87 BPM" drifts to 85.5 in the verse and 88 in the
chorus. After this, it plays over a fixed metronome from the first bar to the last, with the real vocals.

Made for [Notation Hero](https://github.com/Notation-Hero), a drum-practice app, so you can play along to the
original recording over a steady metronome. It works for any instrument, any practice app, any DAW (digital audio
workstation).

- **Offline and free.** Nothing is uploaded.
- **Stems stay locked.** Every stem gets the same time map: vocals, drums, bass and guitar come out the same length
  and in sync.
- **Measures itself.** It re-detects the beats of the result and reports how far off the grid the song was before
  and after.
- **Three beat sources:** detected from the audio, a Guitar Pro 8 file's sync points, or a rhythm-game chart's
  hand-placed tempo map.

Keywords: quantize audio, fix tempo drift, align audio to a click track, time stretch to BPM, beat detection,
tempo map, warp audio to grid, steady tempo, play-along, drum practice, stems.

## Quick start (macOS)

```bash
brew install uv ffmpeg rubberband
git clone https://github.com/Notation-Hero/notation-hero-quantize-audio.git
cd notation-hero-quantize-audio
./quantize-audio --bpm 87 "My Song.mp3"
```

The first run downloads its Python packages and the beat-detection model (about 150 MB). On Linux, install `uv`,
`ffmpeg` and `rubberband` with your package manager.

To run it from any folder, link it into a folder on your `PATH`:

```bash
ln -s "$PWD/quantize-audio" ~/.local/bin/quantize-audio
```

## Use

```bash
# beats detected from the audio: the full mix first, then any stems
quantize-audio --bpm 87 "song.mp3" "vocals.wav" "drums.wav"
# a Guitar Pro 8 file with sync points: its embedded recording ("-" stands for it), numbered by the sync points
quantize-audio --beats gp+auto:"song.gp" -
# a rhythm-game chart's notes.mid (its tempo map was placed by hand on this recording)
quantize-audio --beats chart:notes.mid --bpm 87 "mix.wav" "vocals.opus"
```

It writes a `<song> - quantized` folder next to the song (or `--out FOLDER`) holding:
- the song as `<song>-87bpm.mp3` (320 kbps);
- each stem as `<stem>-87bpm.mp3`, all exactly the same length;
- `report.json` with the tempo of every bar and the before/after measurements.

Add `--wav` for lossless WAV copies beside the MP3s.

It prints a summary:

```text
  tempo 87 BPM; the band played 85.4-87.6
  off the beat (typical / worst 5%): before 149 / 369 ms, after 6 / 15 ms
  drifts: use the quantized file
```

When a song was already recorded to a click, it says so: then it needs only a start offset, not a stretch.

Options:

| Option | What it does |
|---|---|
| `--bpm N` | the tempo to quantize to (strongly recommended with detected beats) |
| `--beats auto` / `gp:FILE` / `gp+auto:FILE` / `chart:FILE` | where the beats come from (default `auto`) |
| `--wav` | also write each result as WAV (lossless) |
| `--click` | also write `before-with-click` and `after-with-click` MP3s: one metronome over the original and the result, to hear the difference |
| `--no-check` | skip measuring the result (a minute faster) |
| `--keep-work` | keep the decoded inputs and time maps |
| `--every 4` | one key point per bar instead of per beat |
| `--engine fine` | Rubber Band's R3 engine instead of R2 with crisp transients |

A chart folder's `song.opus` is **not the full song** when the folder has stems: it is what is left once the stems
are taken out. Sum the stems first and give that as the mix:

```bash
ffmpeg -i song.opus -i vocals.opus -i drums_1.opus -i guitar.opus \
  -filter_complex "amix=inputs=4:normalize=0,alimiter=limit=0.95" mix.wav
```

## How it works

1. **Decode** every input to 44.1 kHz stereo WAV (ffmpeg).
2. **Find the beats**, as (time in the recording, beat number):
   - `auto`: [Beat This!](https://github.com/CPJKU/beat_this) on the mix. Given `--bpm`, it also handles the
     detector's slips: a beat under ¾ of a beat after the last is an "&" and is dropped; a long gap counts its
     missed beats; a beat whose tempo to both neighbours is over 8% off is dropped.
   - `gp:`: each sync point's bar start, from the bar lengths.
   - `gp+auto:`: detected beats, numbered by interpolating the sync points.
   - `chart:`: every quarter note of the chart's tempo map.
3. **Time map:** the first beat stays put; beat *n* goes to `start + n × 60 / bpm`.
4. **Stretch** every input with the same map: `rubberband --crisp 6 -M map -D length`.
5. **Check:** detect the beats of the result and measure each one's distance from the grid. The report splits it
   into **offset** (one number for the whole song, fixed by a start offset) and **jitter** (the spread a metronome
   player hears). `check_drums.py` checks a drum stem without the beat detector, by its onsets.

## How well it works

Tested on five songs (rock and pop, one drumless backing), six runs. Jitter is the typical / worst-5% distance of
a beat from the steady grid:

| Song | Beats from | Before | After |
|---|---|---|---|
| Pop ballad, 87 BPM, full mix + 7 stems | a chart's tempo map | 150 / 359 ms | **6 / 17 ms** |
| The same, mix + vocals | detected | 149 / 369 ms | **6 / 15 ms** |
| Punk rock, 147 BPM | detected, numbered by 15 Guitar Pro sync points | 18 / 58 ms ¹ | **6 / 15 ms** |
| The same | detected | 92 / 203 ms | **6 / 17 ms** |
| Rock, 109 BPM | detected | 12 / 34 ms ² | **6 / 15 ms** |
| Drumless backing, 76 BPM | detected | already steady ² | **6 / 24 ms** |

¹ The file's sync points cover only the first 36 s. ² Already recorded to a click.

On its own, Rubber Band puts every click of a test track wobbling ±3% within ±2 ms of the grid
(`uv run check_drums.py --selftest`).

## Limits today

- One tempo per song. A real tempo change (a slower bridge, a held pause) is pulled onto the grid too.
- Beats are quarter notes: 6/8 and odd meters are not handled yet.
- Guitar Pro files with repeats or jumps are refused by `gp:`.

The roadmap is in [`backlog/`](backlog/) ([Backlog.md](https://backlog.md)): `npx backlog.md board`.

## Licence

**AGPL-3.0-or-later** (see [LICENSE](LICENSE)). You may use, change and share it. If you change it and run it as a
service for others, you must offer them your changed source.

It runs these, each under its own licence:

| Dependency | Used for | Licence |
|---|---|---|
| [Beat This!](https://github.com/CPJKU/beat_this) | beat detection | MIT |
| [PyTorch](https://pytorch.org) | runs the model | BSD-3-Clause |
| [Rubber Band](https://breakfastquay.com/rubberband/) (`rubberband` command) | time-stretching | GPL-2.0-or-later |
| [FFmpeg](https://ffmpeg.org) (`ffmpeg` command) | decoding and encoding | LGPL / GPL |
| [soxr](https://github.com/dofuuz/python-soxr) | resampling (via Beat This!) | LGPL-2.1 |
| numpy, soundfile, mido, einops | maths, WAV files, MIDI, the model | BSD / MIT |
