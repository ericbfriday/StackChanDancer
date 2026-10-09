"""Generate an original 120 BPM bass/treble click track for local testing."""

import argparse
import math
import struct
import wave
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sr, seconds = 22050, 12
    samples = bytearray()
    for frame in range(sr * seconds):
        t = frame / sr
        beat = int(t / .5)
        phase = t - beat * .5
        value = 0.0
        if t >= .5 and phase < .12:
            value = .65 * math.sin(2 * math.pi * 100 * phase) * math.exp(-40 * phase)
            if beat % 2 == 0:
                value += .2 * math.sin(2 * math.pi * 4000 * phase) * math.exp(-80 * phase)
        samples.extend(struct.pack("<h", round(value * 32767)))
    with wave.open(str(args.output), "wb") as wav:
        wav.setparams((1, 2, sr, 0, "NONE", "not compressed"))
        wav.writeframes(samples)
    print(args.output)


if __name__ == "__main__":
    main()
