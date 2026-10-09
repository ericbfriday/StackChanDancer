# StackChanDancer

Desktop audio analysis and bounded choreography for a two-servo Stack-chan.
Python builds a custom `dance.json` timeline; a JavaScript/Moddable example
plays poses and facial expressions against the audio timeline.

**Status:** desktop starter and scheduler tests; physical robot integration
has not been verified. `dance.json` is this project's format, not an upstream
Stack-chan routine standard. Section labels are acoustic heuristics rather
than semantic verse/chorus recognition.

## Quick start on macOS

Install Python 3.11–3.13, Git, and optionally Node.js 20+ for scheduler tests.
FFmpeg is recommended for M4A/AAC or formats unsupported by libsndfile.
For Homebrew users:

```sh
brew install python@3.13 ffmpeg node
git clone https://github.com/ericbfriday/StackChanDancer.git
cd StackChanDancer
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
stackchan-dancer build "/path/to/song.mp3" --out build
stackchan-dancer validate build/dance.json --pcm build/playback.pcm
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/timeline.test.mjs
```

If you already use `uv`, `uv sync --locked --python 3.13` installs the locked
dependencies. Prefix commands with `uv run --locked` instead of activating.
The lock contains platform markers for macOS and Windows; environments are
always rebuilt locally rather than copied between operating systems.

## Quick start on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\stackchan-dancer.exe build "C:\Music\song.wav" --out build
.\.venv\Scripts\stackchan-dancer.exe validate build/dance.json --pcm build/playback.pcm
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/timeline.test.mjs
```

Existing generated files require `--force` to replace. Source audio is never
modified. Audio and build outputs are ignored by Git; transfer music to the
Mac separately. The repository does not distribute any music.

To try an original synthetic 120 BPM track without supplying music:

```sh
python scripts/make_demo.py build/demo-input.wav
stackchan-dancer build build/demo-input.wav --out build/demo
stackchan-dancer validate build/demo/dance.json --pcm build/demo/playback.pcm
```

## Outputs

| File | Purpose |
| --- | --- |
| `features.json` | Beat times, intensity, bass/treble flux, coarse sections |
| `dance.json` | Validated motion-arrival keyframes and face-activation events |
| `playback.wav` | Canonical audio for desktop audition |
| `playback.pcm` | Same samples, mono 22,050 Hz signed little-endian 16-bit PCM |

The PCM digest ties choreography to the exact playback samples. Analyze the
canonical audio once, and play that asset; changing audio timing afterwards
breaks synchronization. The CLI does not upload files or flash a robot.

## How it works

1. Decode, resample, and quantize the audio to the robot playback format.
2. Extract beats and relative intensity; measure bass/treble spectral flux.
3. Estimate acoustic changes in four-second energy/chroma windows.
4. Map beats to pan sweeps and bass nods; add treble expression accents.
5. Bound each smoothstep segment's nominal speed/acceleration and reserve
   enough trajectory budget to return to neutral at the end.
6. Validate the schema, timestamps, motion budgets, sample count and PCM hash.

Read [the architecture and integration guide](docs/architecture.md),
[the v1 format](docs/format.md), and [the Mac transfer guide](docs/mac-transfer.md).

## Firmware

`firmware/dance-player.js` is a hardware-independent timeline evaluator.
`firmware/mod.js`, `pcm-audio.js`, and `manifest.json` are integration examples
for upstream's namespaced context API. Pin the Stack-chan/Moddable revision
and adapt board calibration, host audio ownership, and teardown first.

The included audio clock estimates position from elapsed time. Long-song
playback requires a sample-derived clock and SD streaming. At this PCM
format, one minute occupies 2,646,000 bytes; start with short clips.

The `conservative-v1` profile is illustrative. Measure your chassis before
using it. No physical verification or real-time performance claim is implied.
