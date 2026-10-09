# Architecture and implementation guide

## Division of work

| Layer | Implementation | Responsibility |
| --- | --- | --- |
| Decode/analysis | Python + librosa, NumPy, SciPy, soundfile | Whole-track features |
| Mapping/validation | Python | Deterministic, bounded trajectories and face accents |
| Interchange | Custom versioned JSON + canonical PCM digest | Reproducible asset pair |
| Timeline evaluator | JavaScript | Absolute-time interpolation and event lookup |
| Board adapter | Moddable + Stack-chan capabilities | Servo, face, speaker, lifecycle |

Desktop preprocessing provides future context and avoids competing with
display rendering, I2S audio, and servo communication on the ESP32. On-device
FFT is useful for a future live-reactive mode, but cannot anticipate beats
or see complete song structure. C++ is not needed for the present desktop
pipeline; add a native implementation only for a measured device bottleneck.

## Feature semantics

BPM is beats per minute. The global estimate is metadata; actual beat
timestamps drive choreography, including irregular inter-beat intervals.
Intensity is a robust relative scale within the recording, not absolute
loudness. Bass is 40–250 Hz positive spectral flux; treble is 2.5–9 kHz flux.
The ±four-frame peak window tolerates small beat-tracker alignment errors.

Four-second windows combine energy, band activity and chroma to estimate
structural novelty and idle/steady/energetic/dramatic states. These are not
semantic verse/chorus/breakdown labels. Add repetition analysis or a trained
structure model and manual section overrides if those labels are needed.
The tracker can choose half/double tempo; preview the results before flashing.

## Motion planning

Pan alternates every two beats. Bass transients request downward nods,
with a neutral-tilt recovery between beats. Dance state and beat intensity
scale amplitude. Treble transients activate a 150 ms surprised expression
with at least 350 ms between accents. Expression IDs are project-local.

Between keyframes use `e(u) = 3u² - 2u³`, with `u` normalized to [0,1].
For displacement Δ over T seconds, peak velocity is `1.5 |Δ| / T` and
peak acceleration is `6 |Δ| / T²`. The mapper clips displacement to both
budgets, leaves at least 80 ms between intermediate motion keyframes, and
reserves the sum of remaining segment budgets to finish at neutral.
Velocity is zero at each knot. Acceleration can step at knots; use a jerk-
limited trajectory if your chassis needs smoother reversals.

The default logical coordinates use neutral (90°,90°), pan [70°,110°],
tilt [78°,102°], speed [60°,45°]/s and acceleration [240°,180°]/s².
These are example values, not guaranteed safe values for every servo/chassis.
Changing limits requires a new profile ID and coordinated updates to the
schema, Python constants and firmware validator.

## Synchronization

All time references sample zero of `playback.pcm`. Motion rows specify
arrival times; face rows specify activation times. The scheduler evaluates
absolute playback time and skips obsolete events after delayed callbacks.
It never increments a clock by an assumed timer period or queues stale poses.

The short-clip PCM adapter uses `Time.delta(start)` minus measured output
latency. This avoids accumulated callback-period errors, but it does not
correct I2S clock drift, underruns, or DMA output delay. A production audio
adapter must derive position from output samples consumed, account for
buffered output, and explicitly handle stop/pause/seek/underrun. Queued
AudioOut callbacks provide checkpoints, not automatically exact DAC times.

Mechanical lead advances only the pose track. Calibrate audio latency first,
then mechanical response using a click track and video. A constant lead is
an approximation: response changes with displacement, load and servo type.

## Board integration sequence

1. Identify Core2, CoreS3, or classic M5Stack/Fire and its servo interface.
   Do not assume a universal ST7789 LCD: Core2 uses ILI9342-family hardware.
2. Pin the matching upstream firmware and Moddable toolchain. The inspected
   development API uses `context.motion` and `context.face`; old firmware
   may require another adapter. Angles are radians, yaw positive left and
   pitch positive down. Confirm movement-duration units in that revision.
3. Calibrate servo centers/signs/ranges on the assembled chassis. Use a
   suitably rated servo supply and common ground. Confirm neutral clearance.
4. Build a short clip and validate the PCM digest before packaging. Copy or
   link `firmware/` into the upstream firmware tree and adjust its manifest
   resource paths to this project's generated `build/` files.
5. Confirm the host exports `pins/i2s` to MODs and releases any existing I2S
   owner. Otherwise implement PCM playback inside the host audio service;
   the example cannot assume two AudioOut instances can share the peripheral.
6. Connect `closeDance()` to the actual host MOD teardown hook. Stop timers,
   release the audio output and decide the device's torque policy on exit.
   The example leaves torque policy to the host, including error handling.
7. Verify muted motion, then latency with audio. Test delayed driver calls,
   interruption and disconnection. The example limits catch-up displacement,
   but a device-side acceleration/stall guard is still required for production.

Expression rendering depends on the selected face implementation. Add an
explicit blink/eye-closure or mouth track if deterministic blink/mouth control
is needed; an emotion name alone does not guarantee either.

## Memory and full songs

Parsing JSON creates a heap graph; compact text is not compact RAM. Measure
free heap while audio and rendering are active. Full songs should use SD
audio streaming plus bounded lookahead choreography chunks. Keep shared
motion endpoints across chunks so interpolation stays continuous. A packed
deployment format could use 8-byte motion records (uint32 ms, uint16 pan×100,
uint16 tilt×100) and 5-byte face records. JSON remains the authoring format.

## Primary references

- [Stack-chan source and board support](https://github.com/stack-chan/stack-chan)
- [Namespaced capability API](https://github.com/stack-chan/stack-chan/blob/develop/firmware/docs/api.md)
- [Motion implementation inspected for pose structure/duration](https://github.com/stack-chan/stack-chan/blob/develop/firmware/stackchan/robot.ts)
- [MOD setup](https://github.com/stack-chan/stack-chan/blob/develop/firmware/mods/README.md)
- [Moddable AudioOut](https://github.com/Moddable-OpenSource/moddable/blob/public/documentation/pins/audioout.md)
- [Moddable timing](https://github.com/Moddable-OpenSource/moddable/blob/public/documentation/base/base.md)
- [Librosa 0.11 beat tracker](https://librosa.org/doc/0.11.0/generated/librosa.beat.beat_track.html)
- [Core2 hardware](https://docs.m5stack.com/en/core/Core2)

References were consulted during the design session. Firmware adapters remain
version-sensitive examples; this repository does not vendor upstream code.
