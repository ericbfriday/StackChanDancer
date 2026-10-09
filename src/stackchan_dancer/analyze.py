"""Whole-track analysis; all output timestamps refer to canonical PCM."""

import hashlib
import warnings

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import find_peaks

SR, HOP, FFT = 22050, 256, 2048


def normalize(values):
    values = np.asarray(values, dtype=float)
    return np.clip(values / max(float(np.percentile(values, 95)), 1e-12), 0, 1)


def analyze(source, output):
    """output is an existing Path directory managed by the CLI."""
    y, _ = librosa.load(source, sr=SR, mono=True)
    if not len(y) or not np.all(np.isfinite(y)):
        raise ValueError("Empty or invalid audio")
    duration = round(len(y) * 1000 / SR)
    if not 100 <= duration <= 3600000:
        raise ValueError("Audio duration must be between 100 ms and one hour")

    pcm = np.rint(np.clip(y, -1, 1) * 32767).astype("<i2")
    y = pcm.astype(np.float32) / 32768
    raw = pcm.tobytes()
    (output / "playback.pcm").write_bytes(raw)
    sf.write(output / "playback.wav", y, SR, subtype="PCM_16")

    # Pad analysis only for sub-FFT clips. Playback keeps its exact length.
    analysis_y = np.pad(y, (0, max(0, FFT - len(y))))
    magnitude = np.abs(librosa.stft(analysis_y, n_fft=FFT, hop_length=HOP))
    frequencies = librosa.fft_frequencies(sr=SR, n_fft=FFT)

    def flux(low, high):
        band = magnitude[(frequencies >= low) & (frequencies < high)]
        return normalize(np.maximum(np.diff(
            band, axis=1, prepend=band[:, :1]), 0).mean(axis=0))

    bass, treble = flux(40, 250), flux(2500, 9000)
    energy = normalize(librosa.feature.rms(S=magnitude, frame_length=FFT)[0])
    onset = librosa.onset.onset_strength(y=analysis_y, sr=SR, hop_length=HOP)
    # Near-silence should not be amplified into an energetic dance.
    silent = float(np.max(np.abs(y))) < 1e-4
    if silent:
        bpm, frames = 0.0, np.array([], dtype=int)
    else:
        tempo, frames = librosa.beat.beat_track(
            onset_envelope=onset, sr=SR, hop_length=HOP, trim=True)
        bpm = float(np.asarray(tempo).reshape(-1)[0])
    strength = normalize(onset)

    def ms(frame):
        return round(int(frame) * HOP * 1000 / SR)

    def peak(values, frame):
        frame = min(int(frame), len(values) - 1)
        return float(np.max(values[max(0, frame - 4):frame + 5]))

    beats = []
    for frame in frames:
        if ms(frame) >= duration:
            continue
        level = 0.55 * peak(strength, frame) + 0.45 * peak(energy, frame)
        beats.append({"t_ms": ms(frame), "intensity": level,
                      "class": "strong" if level >= .7 else
                               "medium" if level >= .35 else "weak",
                      "bass": peak(bass, frame), "treble": peak(treble, frame)})

    peaks, _ = find_peaks(treble, height=.65, prominence=.2,
                         distance=round(.30 * SR / HOP))
    treble_events = [] if silent else [ms(f) for f in peaks if ms(f) < duration]

    # Four-second acoustic windows: a heuristic, not semantic verse/chorus.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        chroma = librosa.feature.chroma_stft(S=magnitude ** 2, sr=SR)
    width = round(4 * SR / HOP)
    sections, previous, previous_level = [], None, 0.0
    for start in range(0, magnitude.shape[1], width):
        if ms(start) >= duration:
            break
        stop = min(start + width, magnitude.shape[1])
        level = 0.0 if silent else float(np.mean(energy[start:stop]))
        vector = np.concatenate(([level, np.mean(bass[start:stop]),
                                  np.mean(treble[start:stop])],
                                 np.mean(chroma[:, start:stop], axis=1)))
        novelty = 0.0 if previous is None else float(np.linalg.norm(vector - previous))
        state = ("energetic" if level >= .65 else "idle" if level < .25 else
                 "dramatic" if previous_level - level > .2 else "steady")
        if not sections or state != sections[-1]["state"] or novelty > .8:
            sections.append({"t_ms": ms(start), "state": state, "novelty": novelty})
        previous, previous_level = vector, level

    return {"duration_ms": duration, "bpm": bpm,
            "audio": {"file": "playback.pcm", "sample_rate": SR, "channels": 1,
                      "encoding": "s16le", "samples": len(y),
                      "sha256": hashlib.sha256(raw).hexdigest()},
            "beats": beats, "treble_events_ms": treble_events, "sections": sections}
