import copy
import hashlib
import math
import tempfile
import unittest
import wave
from pathlib import Path

from stackchan_dancer.contract import validate
from stackchan_dancer.mapping import map_dance


def features(duration=4000):
    samples = round(duration * 22050 / 1000)
    return {"duration_ms": duration, "bpm": 120,
            "audio": {"file": "playback.pcm", "sample_rate": 22050,
                      "channels": 1, "encoding": "s16le", "samples": samples,
                      "sha256": "0" * 64},
            "beats": [{"t_ms": t, "intensity": 1, "bass": 1}
                      for t in range(200, duration, 200)],
            "sections": [{"t_ms": 0, "state": "energetic"},
                         {"t_ms": 1000, "state": "dramatic"}],
            "treble_events_ms": [850]}


def write_click_track(path, seconds=8):
    """Original synthetic signal; no copyrighted fixture required."""
    import numpy as np
    sr = 22050
    y = np.zeros(round(sr * seconds), dtype=np.float32)
    for index, t in enumerate(np.arange(.5, seconds - .1, .5)):
        n = round(.12 * sr)
        x = np.arange(n) / sr
        pulse = .65 * np.sin(2 * math.pi * 100 * x) * np.exp(-40 * x)
        if index % 2 == 0:
            pulse += .2 * np.sin(2 * math.pi * 4000 * x) * np.exp(-80 * x)
        start = round(t * sr)
        y[start:start + n] += pulse[:len(y[start:start + n])]
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, sr, 0, "NONE", "not compressed"))
        wav.writeframes(np.rint(np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())


class MappingTests(unittest.TestCase):
    def test_dense_beats_obey_limits_and_finish_neutral(self):
        dance = map_dance(features())
        validate(dance)
        self.assertEqual(dance["motion"][-1], [4000, 90, 90])
        self.assertTrue(any(row[1] != 90 for row in dance["motion"]))

    def test_accent_reset_preserves_transition(self):
        dance = map_dance(features())
        self.assertIn([850, 2], dance["face"])
        self.assertIn([1000, 3], dance["face"])

    def test_no_beats_is_stationary(self):
        data = features(100)
        data["beats"], data["treble_events_ms"] = [], []
        data["sections"] = [{"t_ms": 0, "state": "idle"}]
        dance = map_dance(data)
        self.assertEqual(dance["motion"], [[0, 90, 90], [100, 90, 90]])

    def test_validator_rejects_bad_time_speed_and_nan(self):
        valid = map_dance(features())
        for mutate in (
            lambda d: d["motion"][1].__setitem__(0, 0),
            lambda d: d["motion"][1].__setitem__(1, 110),
            lambda d: d["motion"][1].__setitem__(1, float("nan")),
        ):
            bad = copy.deepcopy(valid)
            mutate(bad)
            with self.assertRaises(Exception):
                validate(bad)

    def test_pcm_digest_is_checked(self):
        dance = map_dance(features(100))
        with tempfile.TemporaryDirectory() as tmp:
            pcm = Path(tmp) / "audio.pcm"
            raw = bytes(dance["audio"]["samples"] * 2)
            pcm.write_bytes(raw)
            dance["audio"]["sha256"] = hashlib.sha256(raw).hexdigest()
            validate(dance, pcm)
            pcm.write_bytes(bytes([1]) + raw[1:])
            with self.assertRaises(ValueError):
                validate(dance, pcm)


class AudioTests(unittest.TestCase):
    def test_click_track_end_to_end(self):
        from stackchan_dancer.analyze import analyze
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "click.wav"
            write_click_track(source)
            data = analyze(source, root)
            dance = map_dance(data)
            validate(dance, root / "playback.pcm")
            self.assertGreater(len(data["beats"]), 8)
            self.assertAlmostEqual(data["bpm"], 120, delta=8)

    def test_silence_has_no_accents(self):
        from stackchan_dancer.analyze import analyze
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "silent.wav"
            with wave.open(str(source), "wb") as wav:
                wav.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
                wav.writeframes(bytes(22050 * 2))
            data = analyze(source, root)
            self.assertEqual(data["beats"], [])
            self.assertEqual(data["treble_events_ms"], [])
            self.assertEqual(map_dance(data)["face"], [[0, 0]])


if __name__ == "__main__":
    unittest.main()
